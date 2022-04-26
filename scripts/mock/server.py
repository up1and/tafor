import os
import datetime

import falcon


root = os.path.abspath(os.path.dirname(__file__))

fir_codes = {
    'ZYTX': ('ZYSH', 'SHENYANG'),
    'ZBAA': ('ZBPE', 'BEIJNG'),
    'ZSHA': ('ZSSS', 'SHANGHAI'),
    'ZHHH': ('ZHWH', 'WUHAN'),
    'ZUUU': ('ZPKM', 'KUNMING'),
    'ZLXY': ('ZLHW', 'LANZHOU '),
    'ZWWW': ('ZWUQ', 'URUMQI'),
    'ZGGG': ('ZGZU', 'GUANGZHOU'),
    'ZJHK': ('ZJSA', 'SANYA'),
    'VHHH': ('VHHK', 'HONGKONG'),
    'YUSO': ('YUDD', 'SHANLON'),
}


class SpecFT24(object):
    tt = 'FT'
    periods = ['0606', '1212', '1818', '0024']
    default = '0024'
    interval = datetime.timedelta(hours=6)
    begin = datetime.timedelta(hours=3)
    duration = datetime.timedelta(hours=24)


def current_taf(time, spec):
    start_of_the_day = datetime.datetime(time.year, time.month, time.day)
    delta = spec.interval - spec.begin

    start_times = {}
    for i, period in enumerate(spec.periods):
        start_times[period] = start_of_the_day + delta + spec.interval * i

    if time < start_of_the_day + spec.interval - spec.begin:
        start_times[spec.default] -= datetime.timedelta(days=1)

    def _find_period(delay):
        for period, start in start_times.items():
            if start <= time < start + delay:
                return period

    period = _find_period(spec.interval)

    if period is None:
        period = spec.default

    start = start_times[period] + spec.begin
    end = start + spec.duration
    
    if '24' in period:
        end -= datetime.timedelta(minutes=1)

    period_with_day = '{}{}/{}{}'.format(str(start.day).zfill(2), period[:2], str(end.day).zfill(2), period[2:])
    return period_with_day


class MessageResource:

    def on_get(self, req, resp, airport):
        now = datetime.datetime.utcnow()
        airport = airport.upper()

        metar = 'METAR {airport} {time}00Z 02004MPS 340V060 8000 BKN007 OVC023 20/19 Q1015 NOSIG='
        taf = 'TAF {airport} {time}Z {period} 04004MPS 4000 BR BKN007 BKN020 TX25/2206Z TN19/2221Z BECMG 2301/2302 SCT020='

        messages = {
            'FT': taf.format(airport=airport, time=now.strftime('%d%H%M'), period=current_taf(now, SpecFT24)),
            'SA': metar.format(airport=airport, time=now.strftime('%d%H')),
        }

        firs = fir_codes.get(airport, None)
        if firs:
            fir, fir_name = firs
            templates = [
                '{fir} SIGMET 2 VALID {start}/{end} {airport}- {fir} {fir_name} FIR EMBD TS FCST ENTIRE FIR TOP FL430 STNR WKN'
            ]

            sigmets = []
            for i, template in enumerate(templates):
                start = now + datetime.timedelta(hours=i * 2)
                end = start + datetime.timedelta(hours=4)

                sigmets.append(template.format(
                    fir=fir,
                    start=start.strftime('%d%H%M'),
                    end=end.strftime('%d%H%M'),
                    airport=airport,
                    fir_name=fir_name,
                ))

            messages.update({'WS': sigmets})

        resp.media = messages


class LayerResource:

    def on_get(self, req, resp):
        resp.media = [
            {
                'extent':[
                    98,
                    0,
                    137,
                    30
                ],
                'image': req.scheme + '://' + req.netloc + '/static/ir_clouds.webp',
                'name': 'Himawari IR Clouds',
                'overlay': 'standalone',
                'proj': '+proj=webmerc +datum=WGS84',
                'updated': falcon.http_now()
            }
        ]


app = falcon.App()
app.add_static_route('/static', os.path.join(root, 'static'))

messages = MessageResource()
layers = LayerResource()

app.add_route('/messages/{airport}', messages)
app.add_route('/layers', layers)


if __name__ == '__main__':
    from waitress import serve
    print('Serving on port 8000...')
    serve(app, port=8000)
