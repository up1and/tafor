import os
import re
import json
import requests

from flask import Flask, request, jsonify, render_template, url_for

from bs4 import BeautifulSoup

BASEDIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, static_url_path='/static')


def find_key(message):
    if message.startswith('METAR'):
        return 'SA'

    if message.startswith('SPECI'):
        return 'SP'

    if message.startswith('TAF'):
        pattern = re.compile(r'(0[1-9]|[12][0-9]|3[0-1])(0024|0606|1212|1818)')
        intl_pattern = re.compile(r'(\d{4})/(\d{4})')
        if pattern.search(message) or intl_pattern.search(message):
            return 'FT'
        else:
            return 'FC'

def marshal(messages):
    resp_dict = {}
    for message in messages:
        resp_dict[find_key(message)] = message

    return resp_dict

def load_fir(mwo, remote=False):
    mwo = mwo.upper()
    boundary_path = os.path.join(BASEDIR, 'config', 'boundary.json')
    with open(boundary_path) as data:
        boundaries = json.load(data)

    file = 'remote.json' if remote else 'local.json'
    info_path = os.path.join(BASEDIR, 'config', file)
    with open(info_path) as data:
        infos = json.load(data)

    info = infos.get(mwo, None)
    info['boundaries'] = boundaries.get(mwo, [])
    return info


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/latest/<airport>.json')
def latest(airport):
    cookies = {
        'LoginCookiesGuid': '5274c2de-632d-4611-ac89-8fc3e173',
        'LoginCookiesName': 'ZJHK'
    }
    url = 'http://172.17.1.166/biz/QueryMetInfo/ReportByArea.aspx'

    try:
        response = requests.get(url, cookies=cookies, timeout=30)
        html = response.content
        soup = BeautifulSoup(html, "html.parser")
        items = [tag.string.strip() for tag in soup.find_all('td') if tag.string is not None]
        messages = list(filter(lambda message: airport.upper() in message, items))

        return jsonify(marshal(messages))

    except Exception as e:
        app.logger.error(e, exc_info=True)
        return jsonify({'error': '{} not found'.format(airport)}), 404

@app.route('/remote/latest/<airport>.json')
def remote_latest(airport):
    url = 'http://www.amsc.net.cn/Page/BaoWenJianSuo/BaoWenJianSuoHandler.ashx'
    post_data = {
        'cmd':'BaoWenJianSuo',
        'IsCCCC': '1', 
        'CCCC': airport, 
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
        response = requests.post(url, params=post_data, timeout=30)
        messages = [msg['RPT'].strip().replace('\n', ' ') for msg in response.json()]

        return jsonify(marshal(messages))

    except Exception as e:
        app.logger.error(e, exc_info=True)
        return jsonify({'error': '{} not found'.format(airport)}), 404

@app.route('/fir/<mwo>.json')
def fir(mwo):
    mwo = mwo.upper()
    url = 'http://192.2.204.51/GetFileName.ashx?type=1&satellite=1&file=IEC'

    try:
        info = load_fir(mwo)
        response = requests.get(url, timeout=2)
        filename = response.text.split('$$')[-1]
        image = 'http://192.2.204.51/FY2_IMAGE/IEC{}.jpg'.format(filename)
        info['image'] = image

    except requests.exceptions.ConnectionError:
        app.logger.warn('GET {} 408 Request Timeout'.format(url))
        return jsonify({'error': '{} not found'.format('satellite image')}), 404

    except Exception as e:
        app.logger.error(e, exc_info=True)
        return jsonify({'error': '{} not found'.format(mwo)}), 404
        
    return jsonify(info)

@app.route('/remote/fir/<mwo>.json')
def remote_fir(mwo):
    mwo = mwo.upper()
    image = url_for('static', filename='{}.jpg'.format(mwo.lower()), _external=True)

    try:
        info = load_fir(mwo, remote=True)
        info['image'] = image
        
    except Exception as e:
        return jsonify({'error': '{} not found'.format(mwo)}), 404

    return jsonify(info)


if __name__ == '__main__':
    import os

    TAFOR_API_ENV = os.environ.get('TAFOR_API_ENV') or 'dev'

    if TAFOR_API_ENV == 'prod':
        debug = False
    else:
        debug = True

    app.run(debug=debug, port=6575)
    