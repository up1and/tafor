from tafor.utils.check import CheckTAF, Listen, remote_message
from tafor.utils.validator import Parser, Validator, REGEX_TAF


def force_bool(value):
    # QSetting 读取的值是字符串类型的 false
    # 转换字符串 false 为布尔值 False   字符串 true 为布尔值 True
    return value if isinstance(value, bool) else value == 'true'