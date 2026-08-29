import pytest

from tafor.core.repositories import MessageRepository, TafRepository
from tafor.ui.components.send import TafSender
from tafor.ui.components.taf import TafEditor


class TestTafEditor:

    @pytest.fixture
    def sender(self, qtbot, context, conf, database):
        sender = TafSender(None, context, conf, repository=MessageRepository(database))
        qtbot.addWidget(sender)
        return sender

    @pytest.fixture
    def editor(self, qtbot, sender, conf, context, database):
        editor = TafEditor(None, sender=sender, conf=conf, context=context, repository=TafRepository(database))
        qtbot.addWidget(editor)
        return editor

    def test_construct(self, editor, conf, context):
        assert editor.primary.state.icao == conf.airport
        assert editor.primary.state.spec == context.taf.spec
        assert len(editor.segments()) == 8
        assert editor.windowTitle()

    def test_normal_period(self, editor):
        primary = editor.primary
        primary.setDate()
        primary.normal.click()

        assert primary.period.text()
        assert primary.state.durations is not None
        assert not primary.sequence.isEnabled()

    def test_amend_sequence(self, editor):
        primary = editor.primary
        primary.setDate()
        primary.amd.click()
        primary.syncToState()

        # Empty database: no amendment this period, so the first one is AAA
        assert primary.sequence.text() == 'AAA'
        assert primary.sequence.isEnabled()
        assert primary.state.type == 'AMD'
        assert primary.state.sequence == 'AAA'

    def test_cancel_mode(self, editor):
        primary = editor.primary
        primary.setDate()
        primary.cnl.click()
        primary.syncToState()

        assert editor.isCancelMode()
        assert all(not c.isEnabled() for c in primary.groupCheckboxs)

        message = primary.message()
        assert message.startswith('TAF AMD ')
        assert message.endswith(' CNL')

    def test_group_visibility(self, editor):
        primary = editor.primary
        checkbox = primary.becmg1Checkbox

        checkbox.setChecked(True)
        editor.updateGroupsVisibility(checkbox)
        assert editor.becmg1.isVisibleTo(editor)

        checkbox.setChecked(False)
        editor.updateGroupsVisibility(checkbox)
        assert not editor.becmg1.isVisibleTo(editor)


if __name__ == '__main__':
    pytest.main()
