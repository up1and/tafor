import os
import re
import json
import calendar
import datetime
import requests

from io import BytesIO
from ftplib import FTP
from functools import partial
from urllib.parse import urlparse

from PIL import Image
from pytz import timezone
from bs4 import BeautifulSoup
from dateutil import relativedelta
from flask import Flask, request, jsonify, abort, render_template, url_for, send_file

ECHO_FTP_HOST = os.environ.get('ECHO_FTP_HOST') or '127.0.0.1'
ECHO_FTP_USER = os.environ.get('ECHO_FTP_USER') or 'root'
ECHO_FTP_PASSWD = os.environ.get('ECHO_FTP_PASSWD') or '123456'
ECHO_FTP_PATH = os.environ.get('ECHO_FTP_PATH') or 'mergeMax'

root = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, static_url_path='/static')

fir_codes = {
    'ZYTX': 'ZYSH',
    'ZBAA': 'ZBPE',
    'ZSHA': 'ZSSS',
    'ZHHH': 'ZHWH',
    'ZUUU': 'ZPKM',
    'ZLXY': 'ZLHW',
    'ZWWW': 'ZWUQ',
    'ZGGG': 'ZGZU',
    'ZJHK': 'ZJSA',
    'VHHH': 'VHHK',
}

def parse_hour_minute(hour, minute, basetime):
    hour = 0 if hour == '24' else int(hour)
    minute = int(minute)

    time = basetime.replace(hour=hour, minute=minute)
    if time <= basetime:
        time = time + datetime.timedelta(days=1)
    return time

def parse_day_hour(day, hour, basetime):
    day = int(day)
    hour = int(hour)
    if hour == 24:
        time = datetime.datetime(basetime.year, basetime.month, day) + datetime.timedelta(days=1)
    else:
        time = datetime.datetime(basetime.year, basetime.month, day, hour)
    return time

def parse_day_hour_minute(day, hour, minute, basetime):
    day = int(day)
    hour = int(hour)
    minute = int(minute)
    time = datetime.datetime(basetime.year, basetime.month, day, hour, minute)
    return time

def generate_day_hour(time, end=False):
    if time.hour == 0 and end:
        time -= datetime.timedelta(hours=1)
        text = '{}24'.format(str(time.day).zfill(2))
    else:
        text = '{}{}'.format(str(time.day).zfill(2), str(time.hour).zfill(2))

    return text

def parse_period(day, period):
    basetime = datetime.datetime.utcnow()
    if int(day) > calendar.monthrange(basetime.year, basetime.month)[1]:
        basetime -= relativedelta.relativedelta(months=1)

    start = parse_day_hour(day, period[:2], basetime)
    end = parse_day_hour(day, period[2:], basetime)
    if end <= start:
        end += datetime.timedelta(days=1)

    return start, end

def parse_intl_period(period):
    start, end = period.split('/')
    basetime = datetime.datetime.utcnow()
    if max([int(start[:2]), int(end[:2])]) > calendar.monthrange(basetime.year, basetime.month)[1]:
        basetime -= relativedelta.relativedelta(months=1)

    if len(start) == 4:
        start = parse_day_hour(start[:2], start[2:], basetime)
        end = parse_day_hour(end[:2], end[2:], basetime)
    else:
        start = parse_day_hour_minute(start[:2], start[2:4], start[4:], basetime)
        end = parse_day_hour_minute(end[:2], end[2:4], end[4:], basetime)

    if end <= start:
        end += relativedelta.relativedelta(months=1)

    return start, end

def parse_basetime(hour, basetime):
    if hour == '24':
        time = datetime.datetime(basetime.year, basetime.month, basetime.day) + datetime.timedelta(days=1)
    else:
        time = datetime.datetime(basetime.year, basetime.month, basetime.day, int(hour))

    if time < basetime:
        time += datetime.timedelta(days=1)

    return time

def parse_interval(interval, basetime):
    start = parse_basetime(interval[:2], basetime)
    end = parse_basetime(interval[2:], basetime)
    if end <= start:
        end += datetime.timedelta(days=1)

    return start, end

def conversion(message):
    message = message.replace('=', '')
    splitPattern = re.compile(r'(BECMG|FM\d{4}|TEMPO|PROB[34]0\sTEMPO|T(?:X|N)M?\d{2}/\d{2}Z)')
    items = [e.strip() for e in splitPattern.split(message) if e.strip()]
    period_pattern = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106|0024|0606|1212|1818)\b')
    interval_pattern = re.compile(r'\b([01][0-9]|2[0-3])([01][0-9]|2[0-4])\b')
    temp_pattern = re.compile(r'T(?:X|N)M?\d{2}/(\d{2})Z')
    fm_pattern = re.compile(r'FM(\d{2})(\d{2})')

    for i, item in enumerate(items):
        m = period_pattern.search(item)
        if m:
            day, period = m.groups()
            start, end = parse_period(day, period)
            basetime = start
            text = '{}/{}'.format(generate_day_hour(start), generate_day_hour(end, end=True))
            items[i] = items[i].replace(m.group(), text)

        m = temp_pattern.match(item)
        if m:
            hour = m.group(1)
            time = parse_basetime(hour, basetime)
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
            start, end = parse_interval(interval, basetime)
            text = '{}/{}'.format(generate_day_hour(start), generate_day_hour(end, end=True))
            items[i] = items[i].replace(interval, text)

        m = fm_pattern.match(item)
        if m:
            hour, minute = m.groups()
            time = parse_hour_minute(hour, minute, basetime)
            text = time.strftime('%d%H%M')
            items[i] = 'FM{}'.format(text)

    return ' '.join(items) + '='

def find_key(message):
    if message.startswith('METAR'):
        return 'SA'

    if message.startswith('SPECI'):
        return 'SP'

    if message.startswith('TAF'):
        ft_pattern = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])(0024|0606|1212|1818)\b')
        fc_pattern = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106)\b')
        international_pattern = re.compile(r'\b(\d{4})/(\d{4})\b')

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

    pieces = message.split()
    if 'AIRMET' in pieces:
        return 'WA'

    if 'SIGMET' in pieces:
        if 'TC' in pieces:
            return 'WC'
        elif 'VA' in pieces:
            return 'WV'
        else:
            return 'WS'

def find_sigmet_period(message):
    pattern = re.compile(r'(\d{6}/\d{6})')
    return pattern.search(message).group()

def marshal(messages, international_mode=False):
    resp_dict = {}
    for message in messages:
        pattern = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106|0024|0606|1212|1818)\b')
        if international_mode and pattern.search(message):
            message = conversion(message)

        resp_dict[find_key(message)] = message

    return resp_dict

def marshal_multiple(messages):
    resp_dict = {}
    for message in messages:
        key = find_key(message)
        if key and key in resp_dict:
            resp_dict[key].append(message)

        if key and key not in resp_dict:
            resp_dict[key] = [message]

    return resp_dict

def load_fir(mwo, remote=False):
    mwo = mwo.upper()
    boundary_path = os.path.join(root, 'config', 'boundary.json')
    with open(boundary_path) as data:
        boundaries = json.load(data)

    file = 'remote.json' if remote else 'local.json'
    layer_path = os.path.join(root, 'config', file)
    with open(layer_path) as data:
        layers = json.load(data)

    info = {}
    info['layers'] = layers.get(mwo, [])
    info['boundaries'] = boundaries.get(mwo, [])
    return info

def build_url(path, url_root=None):
    parser = urlparse(path)
    if parser.scheme:
        url = parser.geturl()
    else:
        url = '{}/{}'.format(url_root.rstrip('/'), parser.geturl().lstrip('/'))

    return url

def himawari8(cat='I'):
    url = 'http://192.2.204.51/GetFileName.ashx?type=3&satellite=2&file={}EA'.format(cat)
    rv = {
        'image': None,
        'updated': None
    }
    response = requests.get(url, timeout=5)
    navie = datetime.datetime.strptime(response.text.strip(), '%Y-%m-%d %H:%M:%S')
    fmt = '%Y%m%d%H%M'
    rv['image'] = 'http://192.2.204.51/HIM_IMAGE/{}/{}EA{}.jpg'.format(cat, cat, navie.strftime(fmt))
    local = timezone('Asia/Shanghai').localize(navie)
    rv['updated'] = local.astimezone(timezone('UTC'))
    return rv

def radar_mosaic():
    rv = {
        'image': None,
        'updated': None
    }
    with FTP(ECHO_FTP_HOST) as ftp:
        ftp.login(user=ECHO_FTP_USER, passwd=ECHO_FTP_PASSWD)
        ftp.cwd(ECHO_FTP_PATH)
        files = ftp.nlst('-t')
        latest = files[-1]

    rv['image'] = url_for('mosaic_image', filename=latest, _external=True)
    navie = datetime.datetime.strptime(latest[1:15], '%Y%m%d%H%M%S')
    local = timezone('Asia/Shanghai').localize(navie)
    rv['updated'] = local.astimezone(timezone('UTC'))
    return rv

def process_echo(source):
    colors = [
        (192, 192, 254, 255), # purple
        (0, 172, 164, 255), # dark green
        (30, 38, 208, 255), # dark blue
        (122, 114, 238, 255), # blue
        # (166, 252, 168, 255), # light green
    ]
    bgcolor = (35, 35, 35, 255)

    origin = Image.open(source)
    image = Image.new('RGBA', (3060, 3060), color=bgcolor)
    image.paste(origin, (-744, -820))
    image = image.resize((1024, 1024))
    pixdata = image.load()
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            if pixdata[x, y] in colors:
                pixdata[x, y] = (0, 0, 0, 255)

    output = BytesIO()
    image.save(output, 'PNG')
    return output


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/messages/<airport>')
def latest_messsage(airport):
    airport = airport.upper()
    fir = fir_codes.get(airport, None)
    cookies = {
        'LoginCookiesGuid': '5274c2de-632d-4611-ac89-8fc3e173',
        'LoginCookiesName': 'ZJHK'
    }
    url = 'http://172.17.1.166/biz/QueryMetInfo/ReportByArea.aspx'
    sigmet_url = 'http://172.17.1.166/biz/warn/list_sigmet.aspx'

    try:
        response = requests.get(url, cookies=cookies, timeout=30)
        html = response.content
        soup = BeautifulSoup(html, 'html.parser')
        items = [tag.string.strip() for tag in soup.find_all('td') if tag.string is not None]
        messages = [m for m in items if airport.upper() in m]
        messages = marshal(messages)

    except Exception as e:
        app.logger.exception(e)
        return jsonify({'error': '{} not found'.format(airport)}), 404

    if fir:
        try:
            endtime = lambda x: parse_intl_period(find_sigmet_period(x))[1]
            response = requests.get(sigmet_url, cookies=cookies, timeout=30)
            html = response.content
            soup = BeautifulSoup(html, 'html.parser')
            items = [tag.string.strip() for tag in soup.find_all('span') if tag.string is not None]
            sigmets = [m for m in items if fir.upper() in m]
            sigmets.sort(key=endtime)
            sigmets = marshal_multiple(sigmets)
            messages.update(sigmets)

        except Exception as e:
            app.logger.exception(e)

    return jsonify(messages)

@app.route('/remote/messages/<airport>')
def remote_latest_message(airport):
    airport = airport.upper()
    fir = fir_codes.get(airport, None)
    url = 'http://www.amsc.net.cn/Page/BaoWenJianSuo/BaoWenJianSuoHandler.ashx'
    post_data = {
        'cmd': 'BaoWenJianSuo',
        'IsCCCC': '1',
        'CCCC': airport,
        'NewCount': 1,
        'StarDate': '',
        'EndDate': '',
        'IsSA': 1,
        'IsSP': 1,
        'IsFC': 1,
        'IsFT': 1,
        'IsOther': '',
        'LianJie': '',
        'YaoSu': '',
        'YunSuanFu': '',
        'ShuZhi': ''
    }

    sigmet_post_data = {
        'cmd': 'BaoWenJianSuo',
        'IsCCCC': '1',
        'CCCC': fir,
        'NewCount': 0,
        'IsSA': 0,
        'IsSP': 0,
        'IsFC': 0,
        'IsFT': 0,
        'IsOther': "'WS''WV''WA''WC'",
        'LianJie': '',
        'YaoSu': '',
        'YunSuanFu': '',
        'ShuZhi': ''
    }

    try:
        response = requests.post(url, params=post_data, timeout=30)
        messages = [msg['RPT'].strip().replace('\n', ' ') for msg in response.json()]
        messages = marshal(messages, international_mode=True)

    except Exception as e:
        app.logger.exception(e)
        return jsonify({'error': '{} not found'.format(airport)}), 404

    if fir:
        try:
            fmt = '%Y-%m-%d %H:%M:%S'
            end = datetime.datetime.utcnow()
            start = end - datetime.timedelta(hours=8)
            sigmet_post_data['StarDate'] = start.strftime(fmt)
            sigmet_post_data['EndDate'] = end.strftime(fmt)

            endtime = lambda x: parse_intl_period(find_sigmet_period(x))[1]
            response = requests.post(url, params=sigmet_post_data, timeout=30)
            sigmets = [msg['RPT'].strip().replace('\n', ' ') for msg in response.json() if endtime(msg['RPT']) >= end]
            sigmets.sort(key=endtime)
            sigmets = marshal_multiple(sigmets)
            messages.update(sigmets)

        except Exception as e:
            app.logger.exception(e)

    return jsonify(messages)


@app.route('/firs/<mwo>')
def fir(mwo):
    mwo = mwo.upper()
    funcs = {
        'Himawari 8 Infrared': himawari8,
        'Himawari 8 Visible': partial(himawari8, cat='V'),
        'Radar Mosaic': radar_mosaic
    }
    try:
        info = load_fir(mwo)

    except Exception as e:
        app.logger.exception(e)
        return jsonify({'error': '{} not found'.format(mwo)}), 404

    for layer in info['layers']:
        image = None
        updated = None

        try:
            func = funcs.get(layer['name'])
            images = func()
            image = images['image']
            updated = images['updated']
        except requests.exceptions.ConnectionError:
            app.logger.warn('GET {} 408 Request Timeout'.format(layer['image']))

        except Exception as e:
            app.logger.exception(e)

        layer['image'] = image
        layer['updated'] = updated

    return jsonify(info)

@app.route('/remote/firs/<mwo>')
def remote_fir(mwo):
    mwo = mwo.upper()
    try:
        info = load_fir(mwo, remote=True)
        for layer in info['layers']:
            layer['image'] = build_url(layer['image'], request.url_root)
            layer['updated'] = datetime.datetime.utcnow()

    except Exception as e:
        app.logger.exception(e)
        return jsonify({'error': '{} not found'.format(mwo)}), 404

    return jsonify(info)

@app.route('/echos/mosaic/<filename>')
def mosaic_image(filename):
    source = BytesIO()
    try:
        with FTP(ECHO_FTP_HOST) as ftp:
            ftp.login(user=ECHO_FTP_USER, passwd=ECHO_FTP_PASSWD)
            ftp.cwd(ECHO_FTP_PATH)
            ftp.retrbinary('RETR {}'.format(filename), source.write)
    except Exception as e:
        abort(404)

    image = process_echo(source)
    image.seek(0)
    return send_file(image, mimetype='image/png')


if __name__ == '__main__':
    TAFOR_API_ENV = os.environ.get('TAFOR_API_ENV') or 'dev'

    if TAFOR_API_ENV == 'prod':
        debug = False
    else:
        debug = True

    app.run(debug=debug, host='0.0.0.0', port=5000)
