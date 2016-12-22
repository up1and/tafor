# -*- coding: utf-8 -*-

import re

class Parser(object):
    """docstring for Validator"""

    regex_taf = {
        'extra': {
                    'ttaaii': r'(FC|FT)CI\d{2}\b',
                    'time': r'(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])\b',
        },

        'common': { 
                    'taf': r'\b(?P<taf>TAF)\b',
                    'icao': r'\b(?P<icao>[A-Z]{4})\b',
                    'timez': r'\b(?P<month>0[1-9]|[12][0-9]|3[0-1])(?P<day>[01][0-9]|2[0-3])(?P<hour>[0-5][0-9])Z\b',
                    'period': r'\b(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106|0024|0606|1212|1818)\b',
                    'wind': r'\b(?:00000|(?P<direction>VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(?P<speed>0[1-9]|[1-4][0-9]|P49)(?:G(?P<gust>0[1-9]|[1-4][0-9]|P49))?)MPS\b',
                    'vis': r'\b(9999|[5-9]000|[01234][0-9]00|0[0-7]50)\b',
                    'wx1': r'\b(NSW|IC|FG|BR|SA|DU|HZ|FU|VA|SQ|PO|FC|TS|FZFG|BLSN|BLSA|BLDU|DRSN|DRSA|DRDU|MIFG|BCFG|PRFG)\b',
                    'wx2': r'\b([-+]?)(DZ|RA|SN|SG|PL|DS|SS|TSRA|TSSN|TSPL|TSGR|TSGS|SHRA|SHSN|SHGR|SHGS|FZRA|FZDZ)\b',
                    'cloud': r'\b(NSC|VV/{3}|VV\d{3}|(FEW|SCT|BKN|OVC)\d{3}(CB|TCU)?)\b',
                    'tmax': r'\b(TXM?(\d{2})/(\d{2})Z)\b',
                    'tmin': r'\b(TNM?(\d{2})/(\d{2})Z)\b',
                    'cavok': r'\bCAVOK\b',
                    'amd': r'\bAMD\b',
                    'cor': r'\bCOR\b',
                    'order': r'\b(CC|AA)([A-Z])\b',
                    'prob': r'\b(PROB[34]0)\b',
                    'sign': r'\b(BECMG|FM|TEMPO|PROB)\b',
                    'interval':r'\b([01][0-9]|2[0-3])([01][0-9]|2[0-3])\b',
        },

        'split': r'(BECMG|FM|TEMPO|PROB[34]0\sTEMPO)\b',
    }

    def __init__(self, message=''):
        self.message = message.replace('=', '')
        self.classify()

    def classify(self):
        self.message_list = re.split(self.regex_taf['split'], self.message)
        self.primary = self.message_list[0]
        self.becmg = list()
        self.tempo = list()
        if len(self.message_list) > 1:
            becmg_index = [i for i, item in enumerate(self.message_list) if item == 'BECMG']
            tempo_index = [i for i, item in enumerate(self.message_list) if 'TEMPO' in item]

            for i, index in enumerate(becmg_index):
                self.becmg.append(self.message_list[index] + self.message_list[index+1])

            # print(self.becmg)

            for i, index in enumerate(tempo_index):
                self.tempo.append(self.message_list[index] + self.message_list[index+1])

            # print(self.tempo)

    def regex(self, message):
        pieces = dict()
        for key, ruler in self.regex_taf['common'].items():
            # print(key, re)
            if key == 'cloud':
                matches = re.findall(ruler, message)
                for index, match in enumerate(matches):
                    pieces.setdefault('cloud' + str(index+1), match)
            else:
                match = re.search(ruler, message)
                if match:
                    pieces.setdefault(key, match.group())
        return pieces


    def process(self):
        self.message_regex = dict()
        self.message_regex['primary'] = self.regex(self.primary)
        for index, item in enumerate(self.becmg):
            self.message_regex.setdefault('becmg' + str(index+1), self.regex(item))

        for index, item in enumerate(self.tempo):
            self.message_regex.setdefault('tempo' + str(index+1), self.regex(item))

        return self.message_regex




class Validator(object):
    """docstring for Validator"""

    @staticmethod
    def wind(str_wind1, str_wind2):
        """
        风：
        1.当预报平均地面风向的变化大于等于 60°，且平均风速在变化前和（或）变化后大于等于 5m/s 时
        2.当预报平均地面风速的变化大于等于 5m/s 时
        3.当预报平均地面风风速变差（阵风）增加大于等于 5m/s，且平均风速在变化前和（或）变化后大于等于 8m/s 时  ***有异议
        """
        regex_wind = re.compile(Parser.regex_taf['common']['wind'])
        wind1 = regex_wind.match(str_wind1).groupdict()
        wind2 = regex_wind.match(str_wind2).groupdict()

        speed1 = int(wind1['speed'])
        speed2 = int(wind2['speed'])

        print(wind1)
        print(wind2)

        def direction():
            # 有一个风向为 VRB, 返回 True
            if 'VRB' in (wind1['direction'], wind2['direction']):
                return True

            direction1 = int(wind1['direction'])
            direction2 = int(wind2['direction'])

            # 计算夹角
            # 风向变化大于180度
            if abs(direction1 - direction2) > 180:
                angle = min(direction1, direction2) + 360 - max(direction1, direction2)
            else:
                angle = abs(direction1 - direction2)

            # print(angle)

            if angle < 60:
                return False

            return True

        # def gust(wind):
        #     if int(wind['gust']) - int(wind['speed']) < 5:
        #         return False

        # 第一条
        if direction() and max(speed1, speed2) >= 5:
            return True

        # 第二条
        if abs(speed1 - speed2) >= 5:
            return True

        # 第三条
        if wind1['gust'] and wind2['gust'] and int(wind2['gust']) - int(wind1['gust']) >= 5 and max(speed1, speed2) >=8:
            return True



    @staticmethod
    def vis(vis1, vis2):
        pass

    @staticmethod
    def weather(wx1, wx2):
        pass

    @staticmethod
    def cloud(cloud1, cloud2):
        pass

print(Validator.wind('36010MPS', '36005MPS'))
