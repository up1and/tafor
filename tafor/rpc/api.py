import os
import json

import falcon

from uuid import uuid4

from tafor import root, conf, logger
from tafor.states import context
from tafor.utils import boolean, TafParser, SigmetParser, MetarParser, AFTNMessageGenerator



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
        'pass': not (parser.tips or not parser.isValid())
    }
    return data

def parse_metar(message, kwargs):
    parser = MetarParser(message, **kwargs)
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
        'pass': not (parser.tips or not parser.isValid())
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
            raise falcon.HTTPBadRequest('Invalid Message', 'Only METAR/SPECI and SIGMET/AIRMET message can be supported.')

        if message.startswith(('METAR', 'SPECI')):
            context.notification.metar.setState({
                'message': message
            })

        if 'SIGMET' in message or 'AIRMET' in message:
            context.notification.sigmet.setState({
                'message': message
            })

        resp.status = falcon.HTTP_CREATED
        resp.media = {
            'message': message,
            'created': falcon.http_now()
        }


class ValidateResource(object):

    @falcon.before(authorize)
    def on_get(self, req, resp):
        message = req.get_param('message') or ''
        message = message.strip()

        kwargs = {
            'visHas5000': boolean(conf.value('Validator/VisHas5000')),
            'cloudHeightHas450': boolean(conf.value('Validator/CloudHeightHas450')),
            'weakPrecipitationVerification': boolean(conf.value('Validator/WeakPrecipitationVerification')),
        }

        if not message:
            raise falcon.HTTPBadRequest('Message Required', 'Please provide the message that needs to be validated.')

        if message.startswith('TAF'):
            data = parse_taf(message, kwargs)
        elif message.startswith('METAR') or message.startswith('SPECI'):
            data = parse_metar(message, kwargs)
        elif 'SIGMET' in message or 'AIRMET' in message:
            data = parse_sigmet(message, kwargs)
        else:
            raise falcon.HTTPBadRequest('Invalid Message', 'The message could not be parsed.')

        resp.media = data


class OtherResource(object):

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


middleware = [JSONComponent(), LoggerComponent()]
server = falcon.App(middleware=middleware, cors_enable=True)

main = MainResource()
state = StateResource()
other = OtherResource()
notification = NotificationResource()
validate = ValidateResource()

server.add_route('/api/state', state)
server.add_route('/api/validate', validate)
server.add_route('/api/others', other)
server.add_route('/api/notifications', notification)

static = webui()
if static:
    server.add_static_route('/', static, fallback_filename=os.path.join(static, 'index.html'))
    server.add_static_route('/static', os.path.join(static, 'static'))
else:
    server.add_route('/', main)
