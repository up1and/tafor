# -*- coding: utf-8 -*-

from .context import tafor

import unittest
import re


class TestParser(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.ruler = tafor.Parser.regex_taf
        self.test_message1 = 'TAF ZGGG 150726Z 150918 03006G20MPS 7000 SA OVC030 BKN040 TX12/12Z TN11/21Z BECMG 1112 36002MPS 3000 -SN BR SCT020 OVC030 BECMG 1415 0800 SN OVC020 PROB30 TEMPO 1518 0550 +SN BKN010 OVC020='
        self.test_message2 = 'TAF ZGGG 240130Z 240312 01004MPS 8000 BKN040 BECMG 0506 5000 -RA OVC030 TEMPO 0611 02008MPS 3000 TSRA FEW010 SCT030CB='
        self.test_message3 = 'TAF ZGGG 150726Z 150918 03003G10MPS 1600 BR OVC040='
        self.test_message4 = 'TAF ZGGG 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR='


    def test_process(self):
        parser = tafor.Parser(self.test_message1)
        print(parser.primary)
        print(parser.process())

    def test_other(self):
        match = re.search(self.ruler['common']['timez'], self.test_message1)
        print(match.groupdict())


class TestValidator(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.validator = tafor.Validator

    def test_wind(self):
        self.assertTrue(self.validator.wind('36010MPS', '36005MPS'))
        self.assertFalse(self.validator.wind('VRB01MPS', '36004MPS'))

    def test_vis(self):
        self.assertTrue(self.validator.vis(1600, 3000))
        self.assertTrue(self.validator.vis(1400, 6000))
        self.assertFalse(self.validator.vis(3000, 1600))

    def test_weather(self):
        self.assertTrue(self.validator.weather('NSW', 'BR'))
        self.assertTrue(self.validator.weather('TS', '-TSRA'))
        self.assertTrue(self.validator.weather('-TSRA', 'TSRA'))
        self.assertFalse(self.validator.weather('TSRA', 'TSRA'))

    def test_clouds(self):
        #self.assertTrue(self.validator.clouds('BKN015', 'SCT007 OVC010'))
        #self.validator.clouds('BKN015', 'SCT007 OVC010')
        print(self.validator.clouds('SCT020', 'SCT020 FEW023CB'))

        


if __name__ == '__main__':
    unittest.main()