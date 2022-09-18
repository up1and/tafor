import os
import json

import falcon

from uuid import uuid4

from sqlalchemy.orm import sessionmaker, scoped_session

from tafor import root, conf, logger
from tafor.models import engine, Taf, Metar, Sigmet, Other
from tafor.states import context
from tafor.utils import boolean, paginate, TafParser, SigmetParser, MetarParser, AFTNMessageGenerator


def as_bool(body, name):
    val = body.get(name)

    if isinstance(val, bool):
        return val

    if val is not None:
        msg = 'The value of the parameter must be "true" or "false".'
        raise falcon.errors.HTTPInvalidParam(msg, name)

def parse_taf(message, kwargs):
    parser = TafParser(message, **kwargs)
    parser.validate()

    tokens = []
    for e in parser.elements:
        for k, token in e.tokens.items():
            pairs = (token['text'], not token['error'])
            tokens.append(pairs)

    data = {
        'html': parser.renderer(style='html'),
        'tokens': tokens,
        'tips': parser.tips,
        'pass': parser.isValid()
    }
    return data

def parse_metar(message, kwargs):
    parser = MetarParser(message, ignoreMetar=True, **kwargs)
    parser.validate()

    tokens = []
    for e in parser.elements[1:]:
        for k, token in e.tokens.items():
            pairs = (token['text'], not token['error'])
            tokens.append(pairs)

    data = {
        'html': parser.renderer(style='html'),
        'tokens': tokens,
        'tips': parser.tips,
        'pass': parser.isValid()
    }
    return data

def parse_sigmet(message, kwargs):
    parser = SigmetParser(message, **kwargs)

    tokens = []
    for e in parser.heads:
        pairs = (e, True)
        tokens.append(pairs)

    for e in parser.elements:
        for token in e.tokens:
            pairs = (token['text'], not token['error'])
            tokens.append(pairs)

    data = {
        'html': parser.renderer(style='html'),
        'tokens': tokens,
        'tips': [],
        'pass': parser.isValid()
    }
    return data

def webui():
    directory = ''
    paths = [os.path.join(root, '..', 'webui'), os.path.join(root, 'webui')]
    for path in paths:
        if os.path.exists(path):
            directory = os.path.abspath(path)
    return directory

def authorize(req, resp, resource, params):
    challenges = ['Bearer Token']

    if req.auth is None:
        description = ('Please provide an auth token as part of the request.')
        raise falcon.HTTPUnauthorized('Bearer Token Required', description, challenges=challenges)

    authType, token = req.auth.split(None, 1)
    if authType == 'Bearer' and token == context.environ.token():
        req.context.user = 'webapi'
    else:
        description = ('The provided auth token is not valid. Please request a new token and try again.')
        raise falcon.HTTPUnauthorized('Authentication Required', description, challenges=challenges)


class LoggerComponent(object):

    def process_response(self, req, resp, resource, req_succeeded):
        logger.info('Request {} - "{} {}" {}'.format(req.remote_addr, req.method, req.relative_uri, resp.status))
        logger.debug('Response {}'.format(resp.media))


class JSONComponent(object):

    def process_request(self, req, resp):
        req.context.body = {}

        if req.content_length in (None, 0):
            return

        body = req.bounded_stream.read()

        try:
            req.context.body = json.loads(body.decode('utf-8'))

        except (ValueError, UnicodeDecodeError):
            raise falcon.HTTPError(falcon.HTTP_753, 'Malformed JSON',
                                   'Could not decode the request body. The JSON was incorrect or not encoded as UTF-8.')


class SQLAlchemySessionComponent(object):
    """
    Create a session for every request and close it when the request ends.
    """

    def __init__(self, db_engine):
        self.engine = db_engine
        self.session_factory = sessionmaker(bind=db_engine)

    def process_resource(self, req, resp, resource, params):
        if req.method == 'OPTIONS':
            return

        req.context['session'] = scoped_session(self.session_factory)

    def process_response(self, req, resp, resource, req_succeeded):
        if req.method == 'OPTIONS':
            return

        if req.context.get('session'):
            if not req_succeeded:
                req.context['session'].rollback()
            req.context['session'].close()


class MainResource(object):

    def on_get(self, req, resp):
        resp.body = ('\nAll in the Sea of Sky, my love\n'
                     'The moonships sail and fly, my love\n'
                     'Though many are their kind, my love\n'
                     'Though all need but one wind\n'
                     'To make their starry way, to make their starry way.\n'
                     '\n'
                     '    ~ The Voyage of the Moon\n')


class StateResource(object):

    @falcon.before(authorize)
    def on_get(self, req, resp):
        data = {
            'aftn': {
                'channel': conf.value('Communication/Channel'),
                'number': conf.value('Communication/ChannelSequenceNumber'),
                'length': conf.value('Communication/ChannelSequenceLength'),
            },
            'address': {
                'taf': conf.value('Communication/TAFAddress'),
                'trend': conf.value('Communication/TrendAddress'),
                'sigmet': conf.value('Communication/SIGMETAddress'),
                'airmet': conf.value('Communication/AIRMETAddress'),
            },
            'originator': conf.value('Communication/OriginatorAddress'),
            'file': {
                'number': conf.value('Communication/FileSequenceNumber'),
            },
            'busy': context.serial.busy(),
            'time': falcon.http_now()
        }
        resp.media = data


class NotificationResource(object):

    @falcon.before(authorize)
    def on_post(self, req, resp):
        message = req.get_param('message') or req.context.body.get('message')
        message = message.strip()

        if not message:
            raise falcon.HTTPBadRequest('Message Required', 'Please provide a notification message.')

        if not (message.startswith(('METAR', 'SPECI')) or 'SIGMET' in message or 'AIRMET' in message):
            raise falcon.HTTPBadRequest('Invalid Message', 'Only SIGMET/AIRMET message can be supported.')

        media = {
            'message': message,
            'created': falcon.http_now()
        }

        if message.startswith(('METAR', 'SPECI')):
            validation = req.get_param_as_bool('validation', blank_as_true=False, default=False) or as_bool(req.context.body, 'validation')

            context.notification.metar.setState({
                'message': message,
                'validation': validation
            })

            if validation:
                kwargs = {
                    'visHas5000': boolean(conf.value('Validation/VisHas5000')),
                    'cloudHeightHas450': boolean(conf.value('Validation/CloudHeightHas450')),
                    'weakPrecipitationVerification': boolean(conf.value('Validation/WeakPrecipitationVerification')),
                }
                media['validations'] = parse_metar(message, kwargs)

        if 'SIGMET' in message or 'AIRMET' in message:
            context.notification.sigmet.setState({
                'message': message
            })

        resp.status = falcon.HTTP_CREATED
        resp.media = media


class ResourceCollection(object):

    def args(self, req):
        page = req.get_param('page') or req.context.body.get('page') or '1'
        limit = req.get_param('limit') or req.context.body.get('limit') or '20'

        page = int(page.strip())
        limit = int(limit.strip())
        return page, limit

    def dump(self, items):
        data = []
        for item in items:
            data.append({
                'uuid': item.uuid,
                'type': item.type,
                'message': item.text,
                'created': falcon.dt_to_http(item.created)
            })
        return data

    def links(self, req, pagination, endpoint):
        info = {}
        params = req.params.copy()
        route = req.prefix + endpoint
        if pagination.hasPrev:
            params['page'] = pagination.prevNum
            url = route + falcon.to_query_str(params)
            info['prev'] = url
        if pagination.hasNext:
            params['page'] = pagination.nextNum
            url = route + falcon.to_query_str(params)
            info['next'] = url

        return info


class MetarsResource(ResourceCollection):

    @falcon.before(authorize)
    def on_get(self, req, resp):
        page, limit = self.args(req)
        queryset = req.context.get('session').query(Metar).order_by(Metar.created.desc())
        pagination = paginate(queryset, page, perPage=limit)

        metars = self.dump(pagination.items)
        links = self.links(req, pagination, '/api/metars')

        resp.media = {
            'metars': metars,
            'links': links
        }


class TafsResource(ResourceCollection):

    @falcon.before(authorize)
    def on_get(self, req, resp):
        page, limit = self.args(req)
        queryset = req.context.get('session').query(Taf).order_by(Taf.created.desc())
        pagination = paginate(queryset, page, perPage=limit)

        tafs = self.dump(pagination.items)
        links = self.links(req, pagination, '/api/tafs')

        resp.media = {
            'tafs': tafs,
            'links': links
        }


class SigmetsResource(ResourceCollection):

    @falcon.before(authorize)
    def on_get(self, req, resp):
        page, limit = self.args(req)
        since = req.get_param('since') or req.context.body.get('since')

        queryset = req.context.get('session').query(Sigmet).order_by(Sigmet.created.desc())

        if since:
            try:
                since = falcon.http_date_to_dt(since)
            except Exception as e:
                raise falcon.HTTPBadRequest('Invalid Parameter', 'Require RFC 1123 date string.')

            queryset = queryset.filter(Sigmet.created > since)

        pagination = paginate(queryset, page, perPage=limit)

        sigmets = self.dump(pagination.items)
        links = self.links(req, pagination, '/api/sigmets')

        resp.media = {
            'sigmets': sigmets,
            'links': links
        }


class OthersResource(ResourceCollection):

    @falcon.before(authorize)
    def on_get(self, req, resp):
        page, limit = self.args(req)

        queryset = req.context.get('session').query(Other).order_by(Other.created.desc())
        pagination = paginate(queryset, page, perPage=limit)

        others = self.dump(pagination.items)
        links = self.links(req, pagination, '/api/others')

        resp.media = {
            'others': others,
            'links': links
        }

    @falcon.before(authorize)
    def on_post(self, req, resp):
        priority = req.get_param('priority') or req.context.body.get('priority')
        address = req.get_param('address') or req.context.body.get('address')
        message = req.get_param('message') or req.context.body.get('message')

        if isinstance(address, list):
            address = ' '.join(address)

        priority = priority.strip()
        address = address.strip()
        message = message.strip()

        if not all([priority, address, message]):
            raise falcon.HTTPBadRequest('Message Required', 'Please provide priority indicator, addresses and message text.')

        uuid = str(uuid4())
        context.other.setState({
            'uuid': uuid,
            'priority': priority,
            'address': address,
            'message': message,
        })

        channel = conf.value('Communication/Channel') or ''
        originator = conf.value('Communication/OriginatorAddress') or ''
        number = conf.value('Communication/ChannelSequenceNumber') or 1
        sequenceLength = conf.value('Communication/ChannelSequenceLength') or 4
        maxSendAddress = conf.value('Communication/MaxSendAddress') or 21

        generator = AFTNMessageGenerator(message, channel=channel, number=number, priority=priority, address=address,
                    originator=originator, sequenceLength=sequenceLength, maxSendAddress=maxSendAddress)

        resp.status = falcon.HTTP_CREATED
        resp.media = {
            'uuid': uuid,
            'message': generator.toString(),
            'type': 'other',
            'created': falcon.http_now()
        }


middleware = [JSONComponent(), LoggerComponent(), SQLAlchemySessionComponent(engine)]
server = falcon.App(middleware=middleware, cors_enable=True)

main = MainResource()
state = StateResource()
metars = MetarsResource()
tafs = TafsResource()
others = OthersResource()
sigmets = SigmetsResource()
notification = NotificationResource()

server.add_route('/api/state', state)
server.add_route('/api/metars', metars)
server.add_route('/api/tafs', tafs)
server.add_route('/api/sigmets', sigmets)
server.add_route('/api/others', others)
server.add_route('/api/notifications', notification)

static = webui()
if static:
    server.add_static_route('/', static, fallback_filename=os.path.join(static, 'index.html'))
    server.add_static_route('/static', os.path.join(static, 'static'))
else:
    server.add_route('/', main)
