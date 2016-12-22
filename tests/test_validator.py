# -*- coding: utf-8 -*-

from .context import tafor

import unittest
import re

test_message1 = 'TAF ZGGG 150726Z 150918 03006G20MPS 7000 SA OVC030 BKN040 TX12/12Z TN11/21Z BECMG 1112 36002MPS 3000 -SN BR SCT020 OVC030 BECMG 1415 0800 SN OVC020 PROB30 TEMPO 1518 0550 +SN BKN010 OVC020='
test_message2 = 'TAF ZGGG 240130Z 240312 01004MPS 8000 BKN040 BECMG 0506 5000 -RA OVC030 TEMPO 0611 02008MPS 3000 TSRA FEW010 SCT030CB='
test_message3 = 'TAF ZGGG 150726Z 150918 03003G10MPS 1600 BR OVC040='
test_message4 = 'TAF ZGGG 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR='


class TestParser(unittest.TestCase):

	@classmethod
	def setUpClass(self):
		self.ruler = tafor.Parser.regex_taf


	def test_process(self):
		parser = tafor.Parser(test_message1)
		print(parser.primary)
		print(parser.process())

	def test_other(self):
		match = re.search(self.ruler['common']['timez'], test_message1)
		print(match.groupdict())


class TestValidator(unittest.TestCase):

	def test_wind(self):
		pass
		


if __name__ == '__main__':
	unittest.main()