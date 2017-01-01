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
                    'timez': r'\b(?P<day>0[1-9]|[12][0-9]|3[0-1])(?P<hour>[01][0-9]|2[0-3])(?P<minute>[0-5][0-9])Z\b',
                    'period': r'\b(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106|0024|0606|1212|1818)\b',
                    'wind': r'\b(?:00000|(?P<direction>VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(?P<speed>0[1-9]|[1-4][0-9]|P49)(?:G(?P<gust>0[1-9]|[1-4][0-9]|P49))?)MPS\b',
                    'vis': r'\b(9999|[5-9]000|[01234][0-9]00|0[0-7]50)\b',
                    'wx1': r'\b(NSW|IC|FG|BR|SA|DU|HZ|FU|VA|SQ|PO|FC|TS|FZFG|BLSN|BLSA|BLDU|DRSN|DRSA|DRDU|MIFG|BCFG|PRFG)\b',
                    'wx2': r'\b([-+]?)(DZ|RA|SN|SG|PL|DS|SS|TSRA|TSSN|TSPL|TSGR|TSGS|SHRA|SHSN|SHGR|SHGS|FZRA|FZDZ)\b',
                    'cloud': r'\bNSC|(?P<cover>FEW|SCT|BKN|OVC)(?P<height>\d{3})(?P<cb>CB|TCU)?\b',
                    'vv':r'\b(VV/{3}|VV\d{3})\b',
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

        'edit':{
                # 'time': r'(?P<day>0[1-9]|[12][0-9]|3[0-1])(?P<hour>[01][0-9]|2[0-3])(?P<minute>[0-5][0-9])',
                'date': r'(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])',
                'wind': r'00000|(VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(0[1-9]|[1-4][0-9]|P49)',
                'gust': r'(0[1-9]|[1-4][0-9]|P49)',
                'vis': r'(9999|[5-9]000|[01234][0-9]00|0[0-7]50)',
                'cloud': r'(FEW|SCT|BKN|OVC)(0[0-4][0-9]|050)',
                'temp': r'M?([0-5][0-9])',
                'hours': r'([01][0-9]|2[0-3])',

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
        3.当预报平均地面风风速变差（阵风）增加(或减少)大于等于 5m/s，且平均风速在变化前和（或）变化后大于等于 8m/s 时  ***有异议
        """
        regex_wind = re.compile(Parser.regex_taf['common']['wind'])
        wind1 = regex_wind.match(str_wind1).groupdict()
        wind2 = regex_wind.match(str_wind2).groupdict()

        speed1 = int(wind1['speed'])
        speed2 = int(wind2['speed'])

        gust1 = int(wind1['gust']) if wind1['gust'] else None
        gust2 = int(wind2['gust']) if wind2['gust'] else None

        # print(wind1, wind2)

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

        # 1.当预报平均地面风向的变化大于等于 60°，且平均风速在变化前和（或）变化后大于等于 5m/s 时
        if direction() and max(speed1, speed2) >= 5:
            return True

        # 2.当预报平均地面风速的变化大于等于 5m/s 时
        if abs(speed1 - speed2) >= 5:
            return True

        # 3.当预报平均地面风风速变差（阵风）增加(或减少)大于等于 5m/s，且平均风速在变化前和（或）变化后大于等于 8m/s 时
        if gust1 and gust2 and abs(gust1 - gust2) >= 5 and max(speed1, speed2) >=8:
            return True

        return False


    @staticmethod
    def vis(vis1, vis2, thresholds=None):
        """
        当预报主导能见度上升并达到或经过下列一个或多个数值，或下降并经过下列一个或多个数值时：
        1. 150 m、350 m、600 m、800 m、1500 m 或 3000 m
        2. 5000 m（当有大量的按目视飞行规则的飞行时） # 我们没有

        """
        trend = 'down' if vis1 > vis2 else 'up'

        # print(vis1, vis2, trend)

        thresholds = thresholds if thresholds else [150, 350, 600, 800, 1500, 3000, 5000]
        for threshold in thresholds:
            if trend == 'up':
                if vis1 < threshold <= vis2:
                    return True
            if trend == 'down':
                if vis2 < threshold < vis1:
                    return True

        return False

        

    @staticmethod
    def weather(wx1, wx2):
        """
        天气现象：
           1. 当预报下列一种或几种天气现象开始、终止或强度变化时：
              冻降水
              中或大的降水（包括阵性降水）包括雷暴
              尘暴
              沙暴

           2. 当预报下列一种或几种天气现象开始、终止时
              冻雾
              低吹尘、低吹沙或低吹雪
              高吹尘、高吹沙或高吹雪
              雷暴（伴或不伴有降水）
              飑
              漏斗云（陆龙卷或水龙卷）
        """
        # regex = r'(BR|HZ|FU|DU|-RA|-SN)'
        # 特殊情况 NSW 未考虑

        regex = r'((?P<intensity>[+-])?(?P<wx1>DZ|RA|SN|SG|PL|DS|SS|SHRA|SHSN|SHGR|SHGS|FZRA|FZDZ|TSRA|TSSN|TSPL|TSGR|TSGS|TSSH)|(?P<wx2>SQ|PO|FC|TS|FZFG|BLSN|BLSA|BLDU|DRSN|DRSA|DRDU))'

        match1 = re.search(regex, wx1)
        match2 = re.search(regex, wx2)

        # print(match1, match2)

        if match1 and match2:
            if match1.group() == match2.group():
                return False

        return True

    @staticmethod
    def clouds(cloud1, cloud2):
        '''   
          当预报BKN或OVC云量的最低云层的云高抬升并达到或经过下列一个或多个数值，或降低并经过下列一个或多个数值时：
            1. 30 m、60 m、150 m 或 300 m
            2. 450 m（在有大量的按目视飞行规则的飞行时）

          当预报低于450 m的云层或云块的量的变化满足下列条件之一时：
            1. 从SCT或更少到BKN、OVC
            2. 从BKN、OVC到SCT或更少

          当预报积雨云将发展或消失时
        '''
        regex = Parser.regex_taf['common']['cloud']
        thresholds = [1, 2, 5, 10, 15]

        # 同为NSC
        if cloud1 == 'NSC' and cloud2 == 'NSC':
            return False

        # 有积雨云CB
        match1 = re.finditer(regex, cloud1)
        match2 = re.finditer(regex, cloud2)
        print(match1)
        print(match2)
        for i in match2:
            print(i.groupdict())




# print(Validator.clouds('SCT020', 'SCT010 FEW023CB'))