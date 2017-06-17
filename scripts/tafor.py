from flask import Flask
from flask import jsonify
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/')
def index():
    return 'Tafor works!'

@app.route('/latest/<icao>.json')
def latest(icao):
    with open('sample.html', 'r') as rv:
        html = rv.read()

    soup = BeautifulSoup(html, "html.parser")
    items = [tag.string.strip() for tag in soup.find_all('td') if tag.string is not None]
    messages = list(filter(lambda message: icao.upper() in message, items))

    if len(messages) == 3:
        return jsonify({'SA': messages[0], 'FT': messages[1], 'FC': messages[2]})

    if len(messages) == 2:
        return jsonify({'SA': messages[0], 'FC': messages[1]})

    if len(messages) == 0:
        return jsonify({'error': '{} not found'.format(icao)})

if __name__ == '__main__':
    app.run(debug=True)