import json

from flask import Flask, Blueprint, Response, request, jsonify, make_response
from werkzeug.exceptions import HTTPException

from tafor.utils import TafParser, SigmetParser

server = Flask(__name__)
api = Blueprint('api', __name__)


def abort(code, **kwargs):
    description = json.dumps(kwargs)
    response = Response(status=code, mimetype='application/json',
                        response=description)
    raise HTTPException(description=description, response=response)

@server.route('/')
def index():
    return 'Tafor RPC is running.'


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
    pass

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

@api.route('/validate', methods=['POST'])
def validate():
    message = request.args.get('message')
    if message.startswith('TAF'):
        kwargs = {
            'visHas5000': request.args.get('visHas5000'),
            'cloudHeightHas450': request.args.get('cloudHeightHas450'),
            'weakPrecipitationVerification': request.args.get('weakPrecipitationVerification'),
        }
        data = parse_taf(message, kwargs)
    elif 'SIGMET' in message or 'AIRMET' in message:
        kwargs = {
            'firCode': request.args.get('firCode'),
            'airportCode': request.args.get('airportCode'),
        }
        data = parse_sigmet(message, kwargs)
    else:
        abort(400, message='The message could not be parsed')

    return jsonify(data)


server.register_blueprint(api, url_prefix='/api')
