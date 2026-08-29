import os
import json
import hmac
import logging

import falcon

from uuid import uuid4

from sqlalchemy.orm import sessionmaker, scoped_session

from tafor.core import root
from tafor.core.models import Metar, Other, Sigmet, Taf
from tafor.core.parsers.metar import MetarParser
from tafor.core.parsers.sigmet import SigmetParser
from tafor.core.parsers.taf import TafParser
from tafor.core.telegram.channels import createChannel
from tafor.core.utils.pagination import paginate

logger = logging.getLogger('tafor.rpc')


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
    challenges = ['Bearer']
    conf = resource.conf

    if req.auth is None:
        description = ('Please provide an auth token as part of the request.')
        raise falcon.HTTPUnauthorized(title='Bearer Token Required', description=description, challenges=challenges)

    parts = req.auth.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        description = ('The Authorization header must use the Bearer scheme.')
        raise falcon.HTTPUnauthorized(title='Authentication Required', description=description, challenges=challenges)

    token = parts[1].strip()
    expected = (conf.authToken or '').encode('utf-8')
    if not hmac.compare_digest(token.encode('utf-8'), expected):
        description = ('The provided auth token is not valid. Please request a new token and try again.')
        raise falcon.HTTPUnauthorized(title='Authentication Required', description=description, challenges=challenges)

    req.context.user = 'webapi'


class LoggerComponent:

    def process_response(self, req, resp, resource, req_succeeded):
        logger.info('Request {} - "{} {}" {}'.format(req.remote_addr, req.method, req.relative_uri, resp.status))
        logger.debug('Response {}'.format(resp.media))


class JSONComponent:

    def process_request(self, req, resp):
        req.context.body = {}

        if req.content_length in (None, 0):
            return

        body = req.bounded_stream.read()

        try:
            req.context.body = json.loads(body.decode('utf-8'))

        except (ValueError, UnicodeDecodeError):
            raise falcon.HTTPBadRequest(title='Malformed JSON',
                                   description='Could not decode the request body. The JSON was incorrect or not encoded as UTF-8.')


class SQLAlchemySessionComponent:
    """
    Create a session for every request and close it when the request ends.
    """

    def __init__(self, db_engine):
        self.engine = db_engine
        self.session_factory = scoped_session(sessionmaker(bind=db_engine))

    def process_resource(self, req, resp, resource, params):
        if req.method == 'OPTIONS':
            return

        req.context['session'] = self.session_factory()

    def process_response(self, req, resp, resource, req_succeeded):
        if req.method == 'OPTIONS':
            return

        if req.context.get('session'):
            if not req_succeeded:
                req.context['session'].rollback()
            req.context['session'].close()


class MainResource:

    def on_get(self, req, resp):
        resp.text = ('\nAll in the Sea of Sky, my love\n'
                     'The moonships sail and fly, my love\n'
                     'Though many are their kind, my love\n'
                     'Though all need but one wind\n'
                     'To make their starry way, to make their starry way.\n'
                     '\n'
                     '    ~ The Voyage of the Moon\n')


class StateResource:

    def __init__(self, context, conf):
        self.context = context
        self.conf = conf

    @falcon.before(authorize)
    def on_get(self, req, resp):
        data = {
            'aftn': {
                'channel': self.conf.channel,
                'number': self.conf.channelSequenceNumber,
                'length': self.conf.channelSequenceLength,
            },
            'address': {
                'taf': self.conf.tafAddress,
                'trend': self.conf.trendAddress,
                'sigmet': self.conf.sigmetAddress,
                'airmet': self.conf.airmetAddress,
            },
            'originator': self.conf.originatorAddress,
            'file': {
                'number': self.conf.fileSequenceNumber,
            },
            'busy': self.context.serial.isBusy,
            'time': falcon.http_now()
        }
        resp.media = data


class NotificationResource:

    def __init__(self, context, conf):
        self.context = context
        self.conf = conf

    @falcon.before(authorize)
    def on_post(self, req, resp):
        message = req.get_param('message') or req.context.body.get('message')
        if message:
            message = message.strip()

        if not message:
            raise falcon.HTTPBadRequest(title='Message Required', description='Please provide a notification message.')

        if not (message.startswith(('METAR', 'SPECI')) or 'SIGMET' in message or 'AIRMET' in message):
            raise falcon.HTTPBadRequest(title='Invalid Message', description='Only SIGMET/AIRMET message can be supported.')

        media = {
            'message': message,
            'created': falcon.http_now()
        }

        if message.startswith(('METAR', 'SPECI')):
            validation = req.get_param_as_bool('validation', blank_as_true=False, default=False) or as_bool(req.context.body, 'validation')

            self.context.notification.metar.setState({
                'message': message,
                'validation': validation
            })

            if validation:
                kwargs = {
                    'visHas5000': self.conf.visHas5000,
                    'cloudHeightHas450': self.conf.cloudHeightHas450,
                    'weakPrecipitationVerification': self.conf.weakPrecipitationVerification,
                }
                media['validations'] = parse_metar(message, kwargs)

        if 'SIGMET' in message or 'AIRMET' in message:
            self.context.notification.sigmet.setState({
                'message': message
            })

        resp.status = falcon.HTTP_CREATED
        resp.media = media


class ResourceCollection:

    def __init__(self, conf):
        self.conf = conf

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
                raise falcon.HTTPBadRequest(title='Invalid Parameter', description='Require RFC 1123 date string.')

            queryset = queryset.filter(Sigmet.created > since)

        pagination = paginate(queryset, page, perPage=limit)

        sigmets = self.dump(pagination.items)
        links = self.links(req, pagination, '/api/sigmets')

        resp.media = {
            'sigmets': sigmets,
            'links': links
        }


class OthersResource(ResourceCollection):

    def __init__(self, context, conf):
        super().__init__(conf)
        self.context = context

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
            raise falcon.HTTPBadRequest(title='Message Required', description='Please provide priority indicator, addresses and message text.')

        uuid = str(uuid4())
        custom = Other(uuid=uuid, text=message, source='api')
        custom.priority = priority
        custom.address = address
        self.context.other.submit(custom)

        generator = createChannel('aftn', self.conf).generate(custom, priority=priority, address=address)

        resp.status = falcon.HTTP_CREATED
        resp.media = {
            'uuid': uuid,
            'message': generator.toString(),
            'type': 'other',
            'created': falcon.http_now()
        }


def create_app(context, engine, conf):
    """Build the falcon application with injectable dependencies.
    """
    middleware = [JSONComponent(), LoggerComponent(), SQLAlchemySessionComponent(engine)]
    app = falcon.App(middleware=middleware, cors_enable=True)

    app.add_route('/api/state', StateResource(context, conf))
    app.add_route('/api/metars', MetarsResource(conf))
    app.add_route('/api/tafs', TafsResource(conf))
    app.add_route('/api/sigmets', SigmetsResource(conf))
    app.add_route('/api/others', OthersResource(context, conf))
    app.add_route('/api/notifications', NotificationResource(context, conf))

    static = webui()
    if static:
        app.add_static_route('/', static, fallback_filename=os.path.join(static, 'index.html'))
        app.add_static_route('/static', os.path.join(static, 'static'))
    else:
        app.add_route('/', MainResource())

    return app
