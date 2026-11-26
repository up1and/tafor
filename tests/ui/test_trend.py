import datetime

import pytest

from tafor.core.repositories import MessageRepository
from tafor.ui.dialogs import TrendEditor, TrendSender


def futurePeriod():
    """A trend period always inside the 2.5h validation window."""
    time = datetime.datetime.utcnow() + datetime.timedelta(minutes=95)
    period = time.strftime('%H%M')
    if period in ('0000', '2400'):
        period = (time + datetime.timedelta(minutes=1)).strftime('%H%M')
    return period


@pytest.fixture
def sender(qtbot, context, conf, database):
    sender = TrendSender(None, context, conf, repository=MessageRepository(database))
    qtbot.addWidget(sender)
    return sender


@pytest.fixture
def editor(qtbot, sender, conf, context):
    editor = TrendEditor(None, sender=sender, conf=conf, context=context)
    qtbot.addWidget(editor)
    return editor


class TestTrendEditor:

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
        assert editor.trend.state.indicator == 'BECMG'
        assert editor.trend.at.isEnabled()

        editor.trend.tempo.click()
        assert editor.trend.state.indicator == 'TEMPO'
        assert not editor.trend.at.isEnabled()

    def test_compose_with_cavok_and_at_period(self, editor):
        period = futurePeriod()
        trend = editor.trend
        trend.becmg.click()
        trend.cavok.click()
        trend.at.click()
        trend.period.setText(period)
        trend.period.textEdited.emit(period)

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

    def test_clear_leaves_next_disabled(self, editor):
        # clear() used to emit contentChanged mid-sweep, while isNosig was
        # still True, so the button kept an enablement that the final, empty
        # state does not justify. TrendPresenter.clear() masked it by
        # disabling the button itself.
        trend = editor.trend
        trend.nosig.click()
        assert editor.nextButton.isEnabled()

        trend.clear()

        assert not trend.state.isAcceptable()
        assert not editor.nextButton.isEnabled()


    def test_edit_without_notification_leaves_the_form_empty(self, editor, context):
        """The reply button is always available, so opening the editor with no
        live METAR notification must not raise -- there is nothing to seed.

        The form does not come up empty: TrendState starts on BECMG, so an
        unseeded form already reads 'BECMG' and stays unacceptable until the
        operator adds a weather group.
        """
        assert context.notification.metar.parser() is None

        editor.edit()

        assert editor.isVisible()
        assert editor.trend.message() == 'BECMG'
        assert not editor.trend.hasAcceptableInput()
        assert not editor.nextButton.isEnabled()


class TestTrendLoading:
    """The form seeds itself from the live METAR's trend group.

    The seed used to go through the widgets: the tokens wrote them, reload()
    read them back, and whatever the widgets could not hold was dropped on
    the way. The tokens now become the state, and populate() renders it.
    """

    def seed(self, context, message):
        context.notification.metar.setState({'message': message, 'validation': True})

    def test_a_trend_group_fills_the_form_and_enables_next(self, editor, context):
        self.seed(context, 'METAR ZJHK 210900Z 14004MPS 4500 TEMPO 24008G15MPS -RA BKN030CB=')

        editor.presenter.loadFromMetar()

        trend = editor.trend
        assert trend.wind.text() == '24008'
        assert trend.gust.text() == '15'
        assert trend.weatherWithIntensity.currentText() == '-RA'
        assert trend.cb.text() == 'BKN030'
        assert trend.message() == 'TEMPO 24008G15MPS -RA BKN030CB'
        assert editor.nextButton.isEnabled()

    def test_a_nosig_metar_checks_nosig(self, editor, context):
        self.seed(context, 'METAR ZJHK 210900Z 14004MPS 4500 BR NSC NOSIG=')

        editor.presenter.loadFromMetar()

        assert editor.trend.nosig.isChecked()
        assert editor.trend.message() == 'NOSIG'
        assert editor.nextButton.isEnabled()

    def test_a_time_group_lands_in_the_period(self, editor, context):
        self.seed(context, 'METAR ZJHK 210900Z 14004MPS 4500 TEMPO FM0915 TL1000 -RA=')

        editor.presenter.loadFromMetar()

        trend = editor.trend
        assert (trend.fm.isChecked(), trend.tl.isChecked()) == (True, True)
        assert trend.period.text() == '0915/1000'

    def test_a_second_load_replaces_what_the_first_wrote(self, editor, context):
        self.seed(context, 'METAR ZJHK 210900Z 14004MPS 4500 TEMPO 24008G15MPS -RA BKN030CB=')
        editor.presenter.loadFromMetar()
        assert editor.trend.cb.text()

        self.seed(context, 'METAR ZJHK 211000Z 25006MPS 9999 TEMPO BR=')
        editor.presenter.loadFromMetar()

        trend = editor.trend
        assert trend.wind.text() == ''
        assert trend.gust.text() == ''
        assert trend.cb.text() == ''
        assert trend.weather.currentText() == 'BR'

    def test_invalid_period_notifies_editor_area(self, editor):
        trend = editor.trend
        trend.becmg.click()
        trend.at.click()
        far = (datetime.datetime.utcnow() + datetime.timedelta(hours=5)).strftime('%H%M')
        trend.period.setText(far)
        trend.period.editingFinished.emit()

        assert trend.period.text() == ''
        assert editor.notificationArea.text() == 'Trend valid time is not correct'


if __name__ == '__main__':
    pytest.main()
