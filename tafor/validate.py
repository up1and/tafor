# -*- coding: utf-8 -*-

import re

taf_message = 'TAF ZGGG 150726Z 150918 03003MPS 1600 BR OVC030 BKN040 TX12/12Z TN11/21Z BECMG 1112 36002MPS 3000 -SN BR SCT020 OVC030 BECMG 1415 0800 SN OVC020 TEMPO 1518 0550 +SN BKN010 OVC020='
# taf_message = 'TAF ZGGG 240130Z 240312 01004MPS 8000 BKN040 BECMG 0506 5000 -RA OVC030 TEMPO 0611 02008MPS 3000 TSRA FEW010 SCT030CB='
# taf_message = 'TAF ZGGG 150726Z 150918 03003G10MPS 1600 BR OVC040='

re_taf = {
        'head': r'(FC|FT)[A-Z]{2}[0-9]{2} [A-Z]{4} [0-9]{6}( CC[A-Z]| AA[A-Z])? ?/',
        'taf': r'(TAF(\sAMD|\sCOR)?)\b',
        'icao': r'\b([A-Z]{4})\b',
        'time': r'\b(\d{6}Z)\b',
        'period': r'\b(\d{6})\b',
        # 'cnl': r'CNL\s?/',
        'wind': r'\b(\d{3}|VRB)(\d{2,3})G?(\d{2,3})?(MPS|KMH|KT)\b',
        'cavok': r'CAVOK',
        'vis': r'\b(\d{4}|P?\dSM)\b',
        'wx1': r'([-+]|\b)(VCSH|NSW|IC|FG|BR|SA|DU|HZ|FU|VA|SQ|PO|FC|TS|BCFG|BLDU|BLSA|BLSN|DRDU|DRSA|DRSN|FZFG|MIFG|PRFG)\b',
        'wx2': r'([-+]|\b)(DZ|RA|SN|SG|PL|DS|SS|FZDZ|FZRA|SHGR|SHGS|SHPL|SHRA|SHSN|TSGR|TSGS|TSPL|TSRA|TSSN|TSSHRA|TSRASN|TSSNRA)\b',
        'vv': r'(VV\d{3}|VV{3})\b',
        'cloud': r'(SKC|NSC|(FEW|SCT|BKN|OVC)\d{3,5}(CB|TCU)?)',
        'tmax': r'TXM?\d{2}/\d{2}Z\b',
        'tmin': r'TNM?\d{2}/\d{2}Z\b',
        # 'becmg': r'(BECMG|FM|TEMPO)\s?\d{4}',
        'split': r'(BECMG|FM|TEMPO)',
        # prob : r'\b(PROB[34]0(\sTEMPO|\sINTER)?|BECMG|TEMPO|FM|INTER)\s?\d{2,4}(\sAND\s\d{2,4})?\s?/
    }

m = re.split(re_taf['split'], taf_message)
print(m)
if m:
    print(m)