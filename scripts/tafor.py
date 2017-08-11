import requests

from flask import Flask
from flask import jsonify

from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/')
def index():
    return 'Tafor works!'

@app.route('/latest/<icao>.json')
def latest(icao):
    try:
        with open('sample.html', 'r') as rv:
            html = rv.read()

        soup = BeautifulSoup(html, "html.parser")
        items = [tag.string.strip() for tag in soup.find_all('td') if tag.string is not None]
        messages = list(filter(lambda message: icao.upper() in message, items))

        if len(messages) == 2:
            return jsonify({'SA': messages[0], 'FC': messages[1]})

        if len(messages) == 3:
            return jsonify({'SA': messages[0], 'FT': messages[2], 'FC': messages[1]})

    except Exception as e:
        return jsonify({'error': '{} not found'.format(icao)}), 404

@app.route('/remote/latest/<icao>.json')
def remote_latest(icao):
    url = "http://www.amsc.net.cn/Page/BaoWenJianSuo/BaoWenJianSuoHandler.ashx"
    post_data = {
        'cmd':'BaoWenJianSuo',
        'IsCCCC': '1', 
        'CCCC': icao, 
        'NewCount':1, 
        'StarDate':'',
        'EndDate':'',
        'IsSA':1, 
        'IsSP':0, 
        'IsFC':1, 
        'IsFT':1,
        'IsOther':'',
        'LianJie':'',
        'YaoSu':'',
        'YunSuanFu':'',
        'ShuZhi':'',
    }

    try:
        response = requests.post(url, params=post_data, timeout=5)
        messages = [msg['RPT'].strip().replace('\n', ' ') for msg in response.json()]

        if len(messages) == 2:
            return jsonify({'SA': messages[0], 'FC': messages[1]})

        if len(messages) == 3:
            return jsonify({'SA': messages[0], 'FT': messages[2], 'FC': messages[1]})

    except Exception as e:
        return jsonify({'error': '{} not found'.format(icao)}), 404


if __name__ == '__main__':
    app.run(debug=True)