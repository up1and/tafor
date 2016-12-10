# -*- coding: utf-8 -*-

import re

taf_message = 'TAF ZGGG 150726Z 150918 03006G20MPS 7000 SA OVC030 BKN040 TX12/12Z TN11/21Z BECMG 1112 36002MPS 3000 -SN BR SCT020 OVC030 BECMG 1415 0800 SN OVC020 PROB30 TEMPO 1518 0550 +SN BKN010 OVC020='
# taf_message = 'TAF ZGGG 240130Z 240312 01004MPS 8000 BKN040 BECMG 0506 5000 -RA OVC030 TEMPO 0611 02008MPS 3000 TSRA FEW010 SCT030CB='
# taf_message = 'TAF ZGGG 150726Z 150918 03003G10MPS 1600 BR OVC040='
taf_message = 'TAF ZGGG 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR='

class Validator(object):
    """docstring for Validator"""

    regex_taf = {
        'normal': {
                    # 'head': r'(FC|FT)[A-Z]{2}[0-9]{2} [A-Z]{4} [0-9]{6}( CC[A-Z]| AA[A-Z])? ?/',
                    # 'taf': r'(TAF(\sAMD|\sCOR)?)\b',
                    # 'icao': r'\b([A-Z]{4})\b',
                    # 'time': r'\b(\d{6}Z)\b',
                    # 'period': r'\b(\d{6})\b',
                    # 'cnl': r'CNL\s?/',
                    # 'wind': r'\b(\d{3}|VRB)(\d{2,3})G?(\d{2,3})?(MPS|KMH|KT)\b',
                    # 'cavok': r'CAVOK',
                    # 'vis': r'\b(\d{4}|P?\dSM)\b',
                    # 'wx1': r'(VCSH|NSW|IC|FG|BR|SA|DU|HZ|FU|VA|SQ|PO|FC|TS|BCFG|BLDU|BLSA|BLSN|DRDU|DRSA|DRSN|FZFG|MIFG|PRFG)\b',
                    # 'wx2': r'([-+]?)(DZ|RA|SN|SG|PL|DS|SS|FZDZ|FZRA|SHGR|SHGS|SHPL|SHRA|SHSN|TSGR|TSGS|TSPL|TSRA|TSSN|TSSHRA|TSRASN|TSSNRA)\b',
                    # 'vv': r'(VV\d{3}|VV{3})\b',
                    # 'cloud': r'(SKC|NSC|(FEW|SCT|BKN|OVC)\d{3,5}(CB|TCU)?)',
                    # 'tmax': r'TXM?\d{2}/\d{2}Z\b',
                    # 'tmin': r'TNM?\d{2}/\d{2}Z\b',
                    # prob : r'\b(PROB[34]0(\sTEMPO|\sINTER)?|BECMG|TEMPO|FM|INTER)\s?\d{2,4}(\sAND\s\d{2,4})?\s?/
        },

        'strict': { 
                    'ttaaii': r'(FC|FT)CI\d{2}\b',
                    'time': r'(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])\b',
                    'taf': r'TAF\b',
                    'cccc': r'([A-Z]{4})\b',
                    'timez': r'(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])Z\b',
                    'period': r'(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106|0024|0606|1212|1818)\b',
                    'wind': r'(?:00000|(VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(0[1-9]|[1-4][0-9]|P49)(?:G(0[1-9]|[1-4][0-9]|P49))?)MPS\b',
                    'vis': r'(9999|[5-9]000|[01234][0-9]00|0[0-7]50)\b',
                    'wx1': r'(NSW|IC|FG|BR|SA|DU|HZ|FU|VA|SQ|PO|FC|TS|FZFG|BLSN|BLSA|BLDU|DRSN|DRSA|DRDU|MIFG|BCFG|PRFG)\b',
                    'wx2': r'([-+]?)(DZ|RA|SN|SG|PL|DS|SS|TSRA|TSSN|TSPL|TSGR|TSGS|SHRA|SHSN|SHGR|SHGS|FZRA|FZDZ)\b',
                    'cloud': r'(NSC|VV/{3}|VV\d{3}|(FEW|SCT|BKN|OVC)\d{3}(CB|TCU)?)\b',
                    'tmax': r'(TXM?(\d{2})/(\d{2})Z)\b',
                    'tmin': r'(TNM?(\d{2})/(\d{2})Z)\b',
                    'prob': r'(PROB[34]0)\b',
                    'cavok': r'CAVOK\b',
                    'amd': r'AMD\b',
                    'cor': r'COR\b',
                    'order': r'(CC|AA)([A-Z])\b',
        },

        'split': r'(BECMG|FM|TEMPO|PROB[34]0\sTEMPO)',
    }

    def __init__(self, message=''):
        self.message = message.replace('=', '')
        self.classify_message()

    def classify_message(self):
        self.message_list = re.split(self.regex_taf['split'], self.message)
        self.primary = self.message_list[0]
        self.becmg = list()
        self.tempo = list()
        if len(self.message_list) >= 3:
            becmg_index = [i for i, item in enumerate(self.message_list) if item == 'BECMG']
            tempo_index = [i for i, item in enumerate(self.message_list) if 'TEMPO' in item]

            # print(becmg_index)
            # print(tempo_index)

            for i, index in enumerate(becmg_index):
                self.becmg.append(self.message_list[index] + self.message_list[index+1])

            # print(self.becmg)

            for i, index in enumerate(tempo_index):
                self.tempo.append(self.message_list[index] + self.message_list[index+1])

            # print(self.tempo)

    def check_wind(self):
        pass

    def check_vis(self):
        pass

    def check_cloud(self):
        pass

    def regex_message(self):
        pass



# m = re.search(re_taf['strict']['cor'], taf_message)
# print(m)
# if m:
#     print(m.groups())

a = Validator(taf_message)

print(a.message_list)