import json

import falcon

from tafor import conf
from tafor.states import context
from tafor.utils import TafParser, SigmetParser, MetarParser


LOGIN_TOKEN = 'VGhlIFZveWFnZSBvZiB0aGUgTW9vbg=='


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
    if authType == 'Bearer' and token == LOGIN_TOKEN:
        req.context.user = 'webapi'
    else:
        description = ('The provided auth token is not valid. Please request a new token and try again.')
        raise falcon.HTTPUnauthorized('Authentication Required', description, challenges)


class MainResource(object):

    def on_get(self, req, resp):
        resp.body = ('\nTafor RPC is running.\n'
                     '\n'
                     '    ~ up1and\n\n')


class StateResource(object):

    @falcon.before(authorize)
    def on_get(self, req, resp):
        data = {
            'sequence': {
                'file': conf.value('Communication/FileSequenceNumber'),
                'aftn': conf.value('Communication/ChannelSequenceNumber'),
            },
            'busy': context.serial.busy(),
            'time': falcon.http_now()
        }
        resp.media = data


class MetarResource(object):

    def on_post(self, req, resp):
        message = req.get_param('message')
        if not message:
            raise falcon.HTTPBadRequest('Message Required', 'Please provide a METAR or SPECI message.')

        context.metar.setState({
            'message': message
        })

        resp.status = falcon.HTTP_CREATED


class ValidateResource(object):

    def on_get(self, req, resp):
        message = req.get_param('message') or ''
        kwargs = {
            'visHas5000': req.get_param('visHas5000') is not None,
            'cloudHeightHas450': req.get_param('cloudHeightHas450') is not None,
            'weakPrecipitationVerification': req.get_param('weakPrecipitationVerification') is not None,
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


server = falcon.API()

main = MainResource()
state = StateResource()
metar = MetarResource()
validate = ValidateResource()

server.add_route('/', main)
server.add_route('/api/state', state)
server.add_route('/api/metar', metar)
server.add_route('/api/validate', validate)
