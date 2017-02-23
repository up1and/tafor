from .aftn import AFTNMessage
from .check import TAFPeriod
from .validator import Parser, Validator, REGEX_TAF


def str2bool(value):
    # QSetting 读取的值是字符串类型的 false
    # 转换字符串 false 为布尔值 False   字符串 true 为布尔值 True
    return value if isinstance(value, bool) else value.lower() in ('true')