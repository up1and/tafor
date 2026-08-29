import datetime

import pytest

from tafor.core.repositories import MessageRepository
from tafor.ui.components.send import TrendSender
from tafor.ui.components.trend import TrendEditor


def futurePeriod():
    """A trend period always inside the 2.5h validation window."""
    time = datetime.datetime.utcnow() + datetime.timedelta(minutes=95)
    period = time.strftime('%H%M')
    if period in ('0000', '2400'):
        period = (time + datetime.timedelta(minutes=1)).strftime('%H%M')
    return period


class TestTrendEditor:

    @pytest.fixture
    def sender(self, qtbot, context, conf, database):
        sender = TrendSender(None, context, conf, repository=MessageRepository(database))
        qtbot.addWidget(sender)
        return sender

    @pytest.fixture
    def editor(self, qtbot, sender, conf, context):
        editor = TrendEditor(None, sender=sender, conf=conf, context=context)
        qtbot.addWidget(editor)
        return editor

    def test_construct(self, editor):
        assert editor.trend.state is not None
        assert not editor.nextButton.isEnabled()

    def test_nosig(self, editor):
        editor.trend.nosig.click()

        assert editor.trend.state.isNosig
        assert editor.trend.message() == 'NOSIG'
        assert editor.nextButton.isEnabled()

        editor.trend.nosig.click()
        assert not editor.trend.state.isNosig

    def test_type_switch(self, editor):
        editor.trend.becmg.click()
        assert editor.trend.state.type == 'BECMG'
        assert editor.trend.at.isEnabled()

        editor.trend.tempo.click()
        assert editor.trend.state.type == 'TEMPO'
        assert not editor.trend.at.isEnabled()

    def test_compose_with_cavok_and_at_period(self, editor):
        period = futurePeriod()
        trend = editor.trend
        trend.becmg.click()
        trend.cavok.click()
        trend.at.click()
        trend.period.setText(period)

        assert editor.nextButton.isEnabled()
        assert trend.message() == 'BECMG AT{} CAVOK'.format(period)

        trend.period.editingFinished.emit()
        assert trend.period.text() == period
        assert trend.message() == 'BECMG AT{} CAVOK'.format(period)

    def test_period_required_with_prefix(self, editor):
        trend = editor.trend
        trend.becmg.click()
        trend.cavok.click()
        trend.at.click()

        assert not editor.nextButton.isEnabled()


if __name__ == '__main__':
    pytest.main()
