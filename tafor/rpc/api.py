from flask import Flask

server = Flask(__name__)

@server.route('/')
def index():
    return 'Tafor RPC is running.'


if __name__ == '__main__':
    server.run(debug=True, port=15400)