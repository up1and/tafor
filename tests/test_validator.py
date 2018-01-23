# -*- coding: utf-8 -*-

from .context import tafor

import unittest
import re


class TestValidator(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.validator = tafor.utils.Validator

    def testWind(self):
        self.assertTrue(self.validator.wind('01004MPS', '07005MPS'))
        self.assertTrue(self.validator.wind('36010MPS', '36005MPS'))
        self.assertTrue(self.validator.wind('03008G15MPS', '36005G10MPS'))
        self.assertTrue(self.validator.wind('03008G13MPS', '36005MPS'))
        self.assertFalse(self.validator.wind('VRB01MPS', '36004MPS'))

    def testVis(self):
        self.assertTrue(self.validator.vis(1600, 3000))
        self.assertTrue(self.validator.vis(1400, 6000))
        self.assertTrue(self.validator.vis(200, 400))
        self.assertFalse(self.validator.vis(3000, 1600))

    def testVv(self):
        self.assertTrue(self.validator.vv('VV002', 'VV005'))
        self.assertFalse(self.validator.vv('VV005', 'VV002'))
        self.assertFalse(self.validator.vv('VV002', 'VV003'))
        
    def testWeather(self):
        self.assertTrue(self.validator.weather('TS', '-TSRA'))
        self.assertTrue(self.validator.weather('-TSRA', 'TSRA'))
        self.assertTrue(self.validator.weather('TSRA BR', '-TSRA'))
        self.assertFalse(self.validator.weather('TSRA', 'TSRA'))
        self.assertFalse(self.validator.weather('NSW', 'BR'))

    def testCloud(self):
        self.assertTrue(self.validator.cloud('BKN015', 'SCT007 OVC010'))
        self.assertTrue(self.validator.cloud('SCT020', 'SCT020 FEW023CB'))
        self.assertTrue(self.validator.cloud('BKN010', 'BKN004'))
        self.assertTrue(self.validator.cloud('SCT007', 'BKN010'))
        self.assertTrue(self.validator.cloud('SCT020', 'BKN010'))
        self.assertFalse(self.validator.cloud('SCT007', 'SCT015'))
        

class TestParser(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.parser = tafor.utils.Parser

    def testMessage(self):
        def validate(message):
            e = self.parser(message)
            isValid = e.validate()

            print(e.renderer(style='terminal'), '\n')
            return isValid
        
        messages = [
            ('TAF ZJHK 150726Z 150918 03003G10MPS 1600 OVC040=', False),
            ('TAF ZJHK 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR=', True),
            ('''TAF ZJHK 240130Z 240312 01004MPS 8000 BKN040 
                BECMG 0506 5000 -RA OVC030 
                TEMPO 0611 02008MPS 3000 TSRA FEW010 SCT030CB=''', False),
            ('''TAF ZJHK 240130Z 240312 01004MPS 8000 BKN040 
                BECMG 0506 5000 -RA FEW010 SCT030CB
                TEMPO 0611 02008MPS 3000 TSRA=''', False),
            ('''TAF ZJHK 150726Z 150918 03006G20MPS 7000 SA OVC030 BKN040 TX12/12Z TN11/21Z 
                BECMG 1112 36002MPS 3000 -SN BR SCT020 OVC030 
                BECMG 1415 0800 SN OVC020 PROB30 
                TEMPO 1518 0550 +SN BKN010 OVC020=''', False),
            ('''TAF AMD ZJHK 211338Z 211524 14004MPS 4500 -RA BKN030
                BECMG 2122 2500 BR BKN012
                TEMPO 1519 07005MPS=''', True),
            ('''TAF ZJHK 211338Z 211524 14004MPS 4500 BKN030
                BECMG 2122 3000 -RA BKN012=''', False),
            ('''TAF ZJHK 211338Z 211524 14004MPS 9999 SCT020 FEW026CB
                BECMG 1718 3000 SHRA
                BECMG 1920 SCT020
                TEMPO 1620 1000 +TSRA
                TEMPO 2024 -SHRA=''', False)
        ]

        for msg, result in messages:
            if result:
                self.assertTrue(validate(msg))
            else:
                self.assertFalse(validate(msg))


if __name__ == '__main__':
    unittest.main()