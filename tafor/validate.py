# -*- coding: utf-8 -*-

import re

taf_message = 'TAF ZGGG 070401Z 070615 02003MPS 8000 NSC TX22/07Z TN17/15Z='

re_taf = {
        'head': r'(FC|FT)[A-Z]{2}[0-9]{2} [A-Z]{4} [0-9]{6}( CC[A-Z]| AA[A-Z])? ?/',
        'taf': r'(TAF(\sAMD|\sCOR)?)\s?/',
        'icao': r'\b([A-Z]{4})\b',
        'time': r'\b(\d{6}Z)\b',
        'period': r'\b(\d{6})\b',
        # 'cnl': r'CNL\s?/',
        'wind': r'\b(\d{3}|VRB)P?(\d{2,3})((G|\/)P?\d{2,3})?\s?(MPS|KMH|KT)\s?',
        'cavok': r'CAVOK\s?/',
        'vis': r'(\d{4}|P?\dSM)\s?/',
        'wx1': r'([-+]|\b)(\/|VCSH|NSW|IC|FG|BR|SA|DU|HZ|FU|VA|SQ|PO|FC|TS|BCFG|BLDU|BLSA|BLSN|DRDU|DRSA|DRSN|FZFG|MIFG|PRFG)\s?',
        'wx2': r'([-+]|\b)(DZ|RA|SN|SG|PL|DS|SS|FZDZ|FZRA|SHGR|SHGS|SHPL|SHRA|SHSN|TSGR|TSGS|TSPL|TSRA|TSSN|TSSHRA|TSRASN|TSSNRA)\s?',
        'vv': r'(VV\d{3}|VV\/{3})\s?',
        'cloud': r'(SKC|NSC|(FEW|SCT|BKN|OVC)[0-9 ]{3,5}(CB|TCU)?)\s?',
        'tmax': r'TXM?\d{2}\/\d{2}Z\s?',
        'tmin': r'TNM?\d{2}\/\d{2}Z\s?',
        'becmg': r'(BECMG|FM|TEMPO)\s?\d{4}\s?',
        # prob : r'\b(PROB[34]0(\sTEMPO|\sINTER)?|BECMG|TEMPO|FM|INTER)\s?\d{2,4}(\sAND\s\d{2,4})?\s?/
    }

m = re.search(re_taf['wind'], taf_message)
print(m)
print(len(m.group()))
