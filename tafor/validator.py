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
                    'taf': r'\b(TAF)\b',
                    'cccc': r'\b([A-Z]{4})\b',
                    'timez': r'\b(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])Z\b',
                    'period': r'\b(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106|0024|0606|1212|1818)\b',
                    'wind': r'\b(?:00000|(VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(0[1-9]|[1-4][0-9]|P49)(?:G(0[1-9]|[1-4][0-9]|P49))?)MPS\b',
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
    def wind(self):
        pass

    @staticmethod
    def vis(self):
        pass

    @staticmethod
    def cloud(self):
        pass


