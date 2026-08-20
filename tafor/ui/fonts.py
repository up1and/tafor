import platform

from PyQt5.QtGui import QFont, QFontDatabase


def uiFont(pointSize=9):
    system = platform.system()
    candidates = {
        'Windows': ['Microsoft YaHei UI', 'Microsoft YaHei', 'Segoe UI', 'SimSun'],
        'Darwin': ['PingFang SC', 'Helvetica Neue', '.AppleSystemUIFont'],
        'Linux': ['Inter', 'Ubuntu', 'Noto Sans SC', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'DejaVu Sans']
    }

    available = set(QFontDatabase().families())
    family = None
    for name in candidates.get(system, []):
        if name in available:
            family = name
            break

    font = QFont()
    if family:
        font.setFamily(family)

    font.setPointSize(pointSize)
    font.setStyleHint(QFont.SansSerif)
    return font


def fixedFont():
    font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    font.setStyleHint(QFont.Monospace)
    return font