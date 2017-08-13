import re
import requests

from flask import Flask
from flask import request, jsonify

from bs4 import BeautifulSoup

app = Flask(__name__)


def find_key(message):
    if message.startswith('METAR'):
        return 'SA'

    if message.startswith('SPECI'):
        return 'SP'

    if message.startswith('TAF'):
        regex = re.compile(r'(0[1-9]|[12][0-9]|3[0-1])(0024|0606|1212|1818)')
        if regex.search(message):
            return 'FT'
        else:
            return 'FC'

def process(messages):
    resp_dict = {}
    for message in messages:
        resp_dict[find_key(message)] = message

    return resp_dict


@app.route('/')
def index():
    return '<h2>Tafor works!</h2> API: {}{}'.format(request.url, 'latest/[icao].json')

@app.route('/latest/<icao>.json')
def latest(icao):
    cookies = {
        'LoginCookiesGuid': '5274c2de-632d-4611-ac89-8fc3e173',
        'LoginCookiesName': 'ZJHK'
    }
    url = 'http://172.17.1.166/biz/QueryMetInfo/ReportByArea.aspx'

    try:
        response = requests.get(url, cookies=cookies)
        html = response.content
        soup = BeautifulSoup(html, "html.parser")
        items = [tag.string.strip() for tag in soup.find_all('td') if tag.string is not None]
        messages = list(filter(lambda message: icao.upper() in message, items))

        return jsonify(process(messages))

    except Exception as e:
        return jsonify({'error': '{} not found'.format(icao)}), 404

@app.route('/remote/latest/<icao>.json')
def remote_latest(icao):
    url = 'http://www.amsc.net.cn/Page/BaoWenJianSuo/BaoWenJianSuoHandler.ashx'
    post_data = {
        'cmd':'BaoWenJianSuo',
        'IsCCCC': '1', 
        'CCCC': icao, 
        'NewCount':1, 
        'StarDate':'',
        'EndDate':'',
        'IsSA':1, 
        'IsSP':1, 
        'IsFC':1, 
        'IsFT':1,
        'IsOther':'',
        'LianJie':'',
        'YaoSu':'',
        'YunSuanFu':'',
        'ShuZhi':'',
    }

    try:
        response = requests.post(url, params=post_data)
        messages = [msg['RPT'].strip().replace('\n', ' ') for msg in response.json()]

        return jsonify(process(messages))

    except Exception as e:
        return jsonify({'error': '{} not found'.format(icao)}), 404


if __name__ == '__main__':
    import os

    TAFOR_SCRIPT_ENV = os.environ.get('TAFOR_SCRIPT_ENV') or 'dev'

    if TAFOR_SCRIPT_ENV == 'prod':
        debug = False
    else:
        debug = True

    app.run(debug=debug)