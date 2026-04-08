from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLayout

from tafor.core.models import Trend
from tafor.ui.widgets import TrendSegment
from tafor.ui.widgets.editor import BaseEditor


class TrendPresenter:
    def __init__(self, view, context, conf):
        self.view = view
        self.context = context
        self.conf = conf

    def initialize(self):
        self.bindSignal()

    def bindSignal(self):
        self.view.trend.contentChanged.connect(self.enableNextButton)
        self.view.nextButton.clicked.connect(self.beforeNext)

    def hasAcceptableInput(self):
        return self.view.trend.hasAcceptableInput()

    def enableNextButton(self):
        self.view.nextButton.setEnabled(self.hasAcceptableInput())

    def beforeNext(self):
        self.view.trend.validate()

        if self.view.isPeriodActive():
            self.view.trend.validatePeriod()

        if self.hasAcceptableInput():
            self.previewMessage()

    def previewMessage(self):
        message = self.view.trend.message()
        self.view.text = message + '='
        message = Trend(text=self.view.text)
        self.view.finished.emit(message)

    def autoFill(self):
        parser = self.context.notification.metar.parser()
        for i, part in enumerate(parser.trends):
            if i == 0:
                self.view.trend.autoFill(part.tokens)

    def clear(self):
        self.view.trend.clear()
        self.view.nextButton.setEnabled(False)


class TrendEditor(BaseEditor):

    def __init__(self, parent=None, sender=None, conf=None, context=None):
        super(TrendEditor, self).__init__(parent, sender, conf, context)
        self.presenter = TrendPresenter(self, context, conf)
        self.initUI()
        self.presenter.initialize()
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Trend Forecast'))

    def initUI(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        layout.setSpacing(18)
        self.trend = TrendSegment(parent=self, conf=self.conf, context=self.context)
        layout.addWidget(self.trend)
        self.addBottomBox(layout)
        self.setLayout(layout)

        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px;}')
        self.trend.metar.setStyleSheet('QLabel {color: grey;}')

    def edit(self):
        self.presenter.autoFill()
        self.show()

    def isPeriodActive(self):
        return self.trend.isPeriodActive()

    def closeEvent(self, event):
        super(TrendEditor, self).closeEvent(event)
        self.presenter.clear()

    def showEvent(self, event):
        if not self.conf.checkCompleteness('trend'):
            QTimer.singleShot(0, self.showConfigError)
