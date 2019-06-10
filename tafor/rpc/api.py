import json

import falcon

from tafor.utils import TafParser, SigmetParser, MetarParser


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


class MainResource(object):

    def on_get(self, req, resp):
        resp.body = ('\nTafor RPC is running.\n'
                     '\n'
                     '    ~ up1and\n\n')


class ValidateResource(object):

    def on_post(self, req, resp):
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
            raise falcon.HTTPBadRequest('Invalid Message',
                                        'The message could not be parsed')

        resp.media = data


server = falcon.API()

main = MainResource()
validate = ValidateResource()

server.add_route('/', main)
server.add_route('/api/validate', validate)
