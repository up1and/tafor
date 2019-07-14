import json

import falcon

from tafor import conf
from tafor.states import context
from tafor.utils import boolean, TafParser, SigmetParser, MetarParser


AUTH_TOKEN = 'VGhlIFZveWFnZSBvZiB0aGUgTW9vbg=='


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

def authorize(req, resp, resource, params):
    challenges = ['Bearer Token']

    if req.auth is None:
        description = ('Please provide an auth token as part of the request.')
        raise falcon.HTTPUnauthorized('Bearer Token Required', description, challenges)

    authType, token = req.auth.split(None, 1)
    if authType == 'Bearer' and token == AUTH_TOKEN:
        req.context.user = 'webapi'
    else:
        description = ('The provided auth token is not valid. Please request a new token and try again.')
        raise falcon.HTTPUnauthorized('Authentication Required', description, challenges)


class CORSComponent(object):

    def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('Access-Control-Allow-Origin', '*')

        if req_succeeded and req.method == 'OPTIONS' and req.get_header('Access-Control-Request-Method'):

            allow = resp.get_header('Allow')
            resp.delete_header('Allow')

            allow_headers = req.get_header(
                'Access-Control-Request-Headers',
                default='*'
            )

            resp.set_headers((
                ('Access-Control-Allow-Methods', allow),
                ('Access-Control-Allow-Headers', allow_headers),
                ('Access-Control-Max-Age', '86400'),  # 24 hours
            ))


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
        resp.body = ('\nTafor RPC is running.\n'
                     '\n'
                     '    ~ up1and\n\n')


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


class MetarResource(object):

    def on_post(self, req, resp):
        message = req.get_param('message') or req.context.body.get('message')
        if not message:
            raise falcon.HTTPBadRequest('Message Required', 'Please provide a METAR or SPECI message.')

        context.metar.setState({
            'message': message
        })

        resp.status = falcon.HTTP_CREATED


class ValidateResource(object):

    def on_get(self, req, resp):
        message = req.get_param('message') or req.context.body.get('message') or ''
        kwargs = {
            'visHas5000': boolean(conf.value('Validator/VisHas5000')),
            'cloudHeightHas450': boolean(conf.value('Validator/CloudHeightHas450')),
            'weakPrecipitationVerification': boolean(conf.value('Validator/WeakPrecipitationVerification')),
        }

        if message.startswith('TAF'):
            data = parse_taf(message, kwargs)
        elif message.startswith('METAR') or message.startswith('SPECI'):
            data = parse_metar(message, kwargs)
        elif 'SIGMET' in message or 'AIRMET' in message:
            data = parse_sigmet(message, kwargs)
        else:
            raise falcon.HTTPBadRequest('Invalid Message', 'The message could not be parsed')

        resp.media = data


middleware = [CORSComponent(), JSONComponent()]
server = falcon.API(middleware=middleware)

main = MainResource()
state = StateResource()
metar = MetarResource()
validate = ValidateResource()

server.add_route('/', main)
server.add_route('/api/state', state)
server.add_route('/api/metar', metar)
server.add_route('/api/validate', validate)
