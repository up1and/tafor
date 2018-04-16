# -*- coding: utf-8 -*-

from .context import tafor

import os
import re
import unittest

root = os.path.dirname(__file__)


def listdir(folder):
    folder = os.path.join(root, 'fixtures', folder)
    files = os.listdir(folder)
    files = filter(lambda o: o.endswith('.text'), files)
    names = map(lambda o: o[:-5], files)
    return folder, names


class TestParser(unittest.TestCase):

    def testTaf(self):
        folder, names = listdir('taf')
        for name in names:
            filepath = os.path.join(folder, name + '.text')
            with open(filepath) as f:
                content = f.read()

            parse = tafor.utils.Parser
            m = parse(content)
            m.validate()
            html = m.renderer(style='html')

            filepath = os.path.join(folder, name + '.html')
            with open(filepath) as f:
                result = f.read()

            html = re.sub(r'\s', '', html)
            result = re.sub(r'\s', '', result)
            self.assertEqual(result, html)


class TestValidator(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.validator = tafor.utils.Validator()

    def testWind(self):
        self.assertTrue(self.validator.wind('01004MPS', '07005MPS'))
        self.assertTrue(self.validator.wind('36010MPS', '36005MPS'))
        self.assertTrue(self.validator.wind('03008G15MPS', '36005G10MPS'))
        self.assertTrue(self.validator.wind('03008G13MPS', '36005MPS'))
        self.assertTrue(self.validator.wind('03004GP49MPS', '36008MPS'))
        self.assertFalse(self.validator.wind('VRB01MPS', '36004MPS'))
        self.assertTrue(self.validator.wind('00000MPS', '07005MPS'))

    def testVis(self):
        self.assertTrue(self.validator.vis(1600, 3000))
        self.assertTrue(self.validator.vis(1400, 6000))
        self.assertTrue(self.validator.vis(200, 400))
        self.assertTrue(self.validator.vis(3000, 1600))
        self.assertTrue(self.validator.vis(4000, 7000))

    def testVv(self):
        self.assertTrue(self.validator.vv('VV002', 'VV005'))
        self.assertTrue(self.validator.vv('VV005', 'VV002'))
        self.assertFalse(self.validator.vv('VV002', 'VV003'))
        
    def testWeather(self):
        self.assertTrue(self.validator.weather('TS', '-TSRA'))
        self.assertTrue(self.validator.weather('-TSRA', 'TSRA'))
        self.assertTrue(self.validator.weather('TSRA BR', '-TSRA'))
        self.assertFalse(self.validator.weather('TSRA', 'TSRA'))
        self.assertFalse(self.validator.weather('NSW', 'BR'))
        self.assertFalse(self.validator.weather('-RA BR', 'BR'))

    def testCloud(self):
        self.assertTrue(self.validator.cloud('BKN015', 'SCT007 OVC010'))
        self.assertTrue(self.validator.cloud('SCT020', 'SCT020 FEW023CB'))
        self.assertTrue(self.validator.cloud('BKN010', 'BKN004'))
        self.assertTrue(self.validator.cloud('SCT007', 'BKN010'))
        self.assertTrue(self.validator.cloud('SCT020', 'BKN010'))
        self.assertFalse(self.validator.cloud('SCT007', 'SCT015'))
        self.assertFalse(self.validator.cloud('NSC', 'SKC'))
        # To be fixed 
        # when cloudHeightHas450 equal False, BKN016, BKN011 always return True


if __name__ == '__main__':
    unittest.main()