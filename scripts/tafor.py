import os
import re
import json
import datetime
import requests

from pytz import timezone
from bs4 import BeautifulSoup

from flask import Flask, jsonify, render_template, url_for

root = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, static_url_path='/static')


def parse_day_hour(utc, day, hour):
    day = int(day)
    hour = int(hour)
    if hour == 24:
        time = datetime.datetime(utc.year, utc.month, day) + datetime.timedelta(days=1)
    else:
        time = datetime.datetime(utc.year, utc.month, day, hour)
    return time

def generate_day_hour(time, end=False):
    if time.hour == 0 and end:
        time -= datetime.timedelta(hours=1)
        text = '{}24'.format(str(time.day).zfill(2))
    else:
        text = '{}{}'.format(str(time.day).zfill(2), str(time.hour).zfill(2))

    return text

def parse_period(day, period):
    utc = datetime.datetime.utcnow()
    start = parse_day_hour(utc, day, period[:2])
    end = parse_day_hour(utc, day, period[2:])
    if end <= start:
        end += datetime.timedelta(days=1)

    return start, end

def parse_intl_period(period):
    start, end = period.split('/')
    utc = datetime.datetime.utcnow()
    start = parse_day_hour(utc, start[:2], start[2:])
    end = parse_day_hour(utc, end[:2], end[2:])
    return start, end

def parse_basetime(basetime, hour):
    if hour == '24':
        time = datetime.datetime(basetime.year, basetime.month, basetime.day) + datetime.timedelta(days=1)
    else:
        time = datetime.datetime(basetime.year, basetime.month, basetime.day, int(hour))

    if time < basetime:
        time += datetime.timedelta(days=1)

    return time

def parse_interval(basetime, interval):
    start = parse_basetime(basetime, interval[:2])
    end = parse_basetime(basetime, interval[2:])
    if end <= start:
        end += datetime.timedelta(days=1)

    return start, end

def conversion(message):
    message = message.replace('=', '')
    items = message.split()
    period_pattern = re.compile(r'(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106|0024|0606|1212|1818)')
    interval_pattern = re.compile(r'\b([01][0-9]|2[0-3])([01][0-9]|2[0-4])\b')
    temp_pattern = re.compile(r'T(?:X|N)M?\d{2}/(\d{2})Z')

    for i, item in enumerate(items):
        m = period_pattern.match(item)
        if m:
            day, period = m.groups()
            start, end = parse_period(day, period)
            basetime = start
            items[i] = '{}/{}'.format(generate_day_hour(start), generate_day_hour(end, end=True))

        m = temp_pattern.match(item)
        if m:
            hour = m.group(1)
            time = parse_basetime(basetime, hour)
            day_hour = generate_day_hour(time)

            if '{}0009'.format(day) in message:
                day_hour = generate_day_hour(time)

            if '{}1524'.format(day) in message:
                day_hour = generate_day_hour(time, end=True)

            if '{}0024'.format(day) in message:
                if hour == '00':
                    day_hour = generate_day_hour(time)
                if hour == '24':
                    day_hour = generate_day_hour(time, end=True)

            items[i] = '{}{}Z'.format(item[:-3], day_hour)

        m = interval_pattern.match(item)
        if m:
            interval = m.group()
            start, end = parse_interval(basetime, interval)
            items[i] = '{}/{}'.format(generate_day_hour(start), generate_day_hour(end, end=True))

    return ' '.join(items) + '='

def find_key(message):
    if message.startswith('METAR'):
        return 'SA'

    if message.startswith('SPECI'):
        return 'SP'

    if message.startswith('TAF'):
        ft_pattern = re.compile(r'(0[1-9]|[12][0-9]|3[0-1])(0024|0606|1212|1818)')
        fc_pattern = re.compile(r'(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106)')
        international_pattern = re.compile(r'(\d{4})/(\d{4})')

        if fc_pattern.search(message):
            return 'FC'

        if ft_pattern.search(message):
            return 'FT'

        m = international_pattern.search(message)
        if m:
            start, end = parse_intl_period(m.group())
            if end - start < datetime.timedelta(hours=24):
                return 'FC'
            else:
                return 'FT'

def marshal(messages, international_mode=False):
    resp_dict = {}
    for message in messages:
        pattern = re.compile(r'(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106|0024|0606|1212|1818)')
        if international_mode and pattern.search(message):
            message = conversion(message)

        resp_dict[find_key(message)] = message

    return resp_dict

def load_fir(mwo, remote=False):
    mwo = mwo.upper()
    boundary_path = os.path.join(root, 'config', 'boundary.json')
    with open(boundary_path) as data:
        boundaries = json.load(data)

    file = 'remote.json' if remote else 'local.json'
    info_path = os.path.join(root, 'config', file)
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
        app.logger.exception(e)
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
        'ShuZhi':''
    }

    try:
        response = requests.post(url, params=post_data, timeout=30)
        messages = [msg['RPT'].strip().replace('\n', ' ') for msg in response.json()]

        return jsonify(marshal(messages, international_mode=True))

    except Exception as e:
        app.logger.exception(e)
        return jsonify({'error': '{} not found'.format(airport)}), 404

@app.route('/fir/<mwo>.json')
def fir(mwo):
    mwo = mwo.upper()
    url = 'http://192.2.204.51/GetFileName.ashx?type=1&satellite=1&file=IEC'
    image = None
    updated = None

    try:
        info = load_fir(mwo)

    except Exception as e:
        app.logger.exception(e)
        return jsonify({'error': '{} not found'.format(mwo)}), 404

    try:
        response = requests.get(url, timeout=2)
        filename = response.text.split('$$')[-1]
        image = 'http://192.2.204.51/FY2_IMAGE/IEC{}.jpg'.format(filename)
        fmt = '%Y%m%d%H%M'
        navie = datetime.datetime.strptime(filename, fmt)
        local = timezone('Asia/Shanghai').localize(navie)
        updated = local.astimezone(timezone('UTC'))

    except requests.exceptions.ConnectionError:
        app.logger.warn('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        app.logger.exception(e)

    info['image'] = image
    info['updated'] = updated

    return jsonify(info)

@app.route('/remote/fir/<mwo>.json')
def remote_fir(mwo):
    mwo = mwo.upper()
    image = url_for('static', filename='{}.jpg'.format(mwo.lower()), _external=True)

    try:
        info = load_fir(mwo, remote=True)
        info['image'] = image
        info['updated'] = datetime.datetime.utcnow()

    except Exception as e:
        app.logger.exception(e)
        return jsonify({'error': '{} not found'.format(mwo)}), 404

    return jsonify(info)


if __name__ == '__main__':
    TAFOR_API_ENV = os.environ.get('TAFOR_API_ENV') or 'dev'

    if TAFOR_API_ENV == 'prod':
        debug = False
    else:
        debug = True

    app.run(debug=debug, port=6575)
    