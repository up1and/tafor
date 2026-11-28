import ast
from pathlib import Path

from PyQt5.QtWidgets import QCheckBox, QComboBox, QLineEdit, QRadioButton, QTextEdit

from tafor.ui.forms import (
    FormPipeline,
    setChecked,
    setComboOptions,
    setComboText,
    setLineText,
    setPlainText,
)


class TestFormPipeline:

    def test_pipeline_module_does_not_import_pyqt5(self):
        pipelinePath = Path(__file__).resolve().parents[2] / 'tafor' / 'ui' / 'forms' / 'pipeline.py'
        tree = ast.parse(pipelinePath.read_text(encoding='utf-8'))

        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)

        assert not any(name.startswith('PyQt5') for name in imported)

    def test_edit_runs_stages_in_order_and_tracks_previous(self):
        calls = []
        state = {'wind': '', 'gust': ''}

        def apply(raw):
            calls.append(('apply', dict(raw)))
            state['wind'] = raw.get('wind', '')
            state['gust'] = raw.get('gust', '')

        def rules(raw, previous, changed, source):
            calls.append(('rules', dict(raw), dict(previous), set(changed), source))

        def render():
            calls.append(('render', dict(state)))

        def changed():
            calls.append(('changed',))

        def effect(changedFields, source):
            calls.append(('effect', set(changedFields), source))

        pipeline = FormPipeline(
            {'wind': '', 'gust': ''},
            apply=apply,
            rules=rules,
            render=render,
            changed=changed,
            effect=effect,
        )

        applied = pipeline.edit({'wind': '24008'})

        assert applied is True
        assert pipeline.value('wind') == '24008'
        assert pipeline.previous == {'wind': '', 'gust': ''}
        assert calls == [
            ('apply', {'wind': '24008', 'gust': ''}),
            ('rules', {'wind': '24008', 'gust': ''}, {'wind': '', 'gust': ''}, {'wind'}, 'user'),
            ('render', {'wind': '24008', 'gust': ''}),
            ('changed',),
            ('effect', {'wind'}, 'user'),
        ]

    def test_edit_skips_when_patch_matches_raw_unless_forced(self):
        renders = 0
        changes = 0
        effects = []

        def render():
            nonlocal renders
            renders += 1

        def changed():
            nonlocal changes
            changes += 1

        def effect(changedFields, source):
            effects.append((set(changedFields), source))

        pipeline = FormPipeline(
            {'wind': '24008'},
            render=render,
            changed=changed,
            effect=effect,
        )

        assert pipeline.edit({'wind': '24008'}) is False
        assert pipeline.edit({}) is False
        assert renders == 0
        assert changes == 0
        assert effects == []

        assert pipeline.edit({'wind': '24008'}, source='clock', force=True) is True
        assert renders == 1
        assert changes == 1
        assert effects == [({'wind'}, 'clock')]

    def test_partial_raw_input_kept_while_domain_state_stays_empty(self):
        state = {'wind': ''}

        def apply(raw):
            value = raw.get('wind', '')
            state['wind'] = value if len(value) == 5 else ''

        pipeline = FormPipeline({'wind': ''}, apply=apply)

        pipeline.edit({'wind': '120'})
        assert pipeline.value('wind') == '120'
        assert state['wind'] == ''

        pipeline.edit({'wind': '12015'})
        assert pipeline.value('wind') == '12015'
        assert state['wind'] == '12015'

    def test_rules_mutating_raw_triggers_second_apply_and_keeps_previous(self):
        applyCalls = []
        state = {'period': '', 'wind': '00000', 'gust': '15'}

        def apply(raw):
            applyCalls.append(dict(raw))
            state['period'] = raw.get('period', '')
            state['wind'] = raw.get('wind', '')
            state['gust'] = raw.get('gust', '')

        def rules(raw, previous, changed, source):
            if 'period' in changed and len(raw['period']) > len(previous.get('period', '')) and len(raw['period']) == 4:
                raw['period'] = raw['period'] + '/'
            if raw.get('wind') == '00000':
                raw['gust'] = ''

        pipeline = FormPipeline(
            {'period': '101', 'wind': '00000', 'gust': '15'},
            apply=apply,
            rules=rules,
        )

        pipeline.edit({'period': '1012'})

        assert pipeline.value('period') == '1012/'
        assert pipeline.value('gust') == ''
        assert pipeline.previous['period'] == '101'
        assert state['period'] == '1012/'
        assert state['gust'] == ''
        assert len(applyCalls) == 2

        pipeline.edit({'period': '1012'})
        assert pipeline.previous['period'] == '1012/'
        assert pipeline.value('period') == '1012'

    def test_validate_scope_with_rejection_clears_raw_and_state_and_rerenders(self):
        state = {'wind': '24010', 'gust': '12'}
        renders = 0
        changes = 0
        effects = []
        notifications = []

        def apply(raw):
            state['wind'] = raw.get('wind', '')
            state['gust'] = raw.get('gust', '')

        def rules(raw, previous, changed, source):
            effects.append(('rules', set(changed), source))

        def validator(scope):
            if scope in (None, 'gust') and state['gust'] == '12':
                return ({'gust': ''}, ['gust_too_low'])
            return ({}, [])

        def render():
            nonlocal renders
            renders += 1

        def changed():
            nonlocal changes
            changes += 1

        def effect(changedFields, source):
            effects.append(('effect', set(changedFields), source))

        pipeline = FormPipeline(
            {'wind': '24010', 'gust': '12'},
            apply=apply,
            rules=rules,
            validator=validator,
            render=render,
            notify=notifications.append,
            changed=changed,
            effect=effect,
        )

        errors = pipeline.validate('gust')

        assert errors == ['gust_too_low']
        assert pipeline.value('gust') == ''
        assert state['gust'] == ''
        assert renders == 1
        assert changes == 1
        assert notifications == ['gust_too_low']
        assert effects == [
            ('rules', {'gust'}, 'validate'),
            ('effect', {'gust'}, 'validate'),
        ]

    def test_validate_scope_with_normalization_patch_updates_without_notifying(self):
        state = {'period': '2400'}
        renders = 0
        notifications = []

        def apply(raw):
            state['period'] = raw.get('period', '')

        def validator(scope):
            if scope == 'period' and state['period'] == '2400':
                return ({'period': '0000'}, [])
            return ({}, [])

        def render():
            nonlocal renders
            renders += 1

        pipeline = FormPipeline(
            {'period': '2400'},
            apply=apply,
            validator=validator,
            render=render,
            notify=notifications.append,
        )

        errors = pipeline.validate('period')

        assert errors == []
        assert pipeline.value('period') == '0000'
        assert state['period'] == '0000'
        assert renders == 1
        assert notifications == []

    def test_validate_scope_noop_and_error_without_patch(self):
        renders = 0
        changes = 0
        notifications = []
        mode = 'ok'

        def validator(scope):
            if mode == 'ok':
                return ({}, [])
            return ({}, ['warn_only'])

        def render():
            nonlocal renders
            renders += 1

        def changed():
            nonlocal changes
            changes += 1

        pipeline = FormPipeline(
            {'wind': '24008'},
            validator=validator,
            render=render,
            notify=notifications.append,
            changed=changed,
        )

        assert pipeline.validate('wind') == []
        assert renders == 0
        assert changes == 0
        assert notifications == []

        mode = 'warn'
        assert pipeline.validate('wind') == ['warn_only']
        assert renders == 0
        assert changes == 0
        assert notifications == ['warn_only']

    def test_validate_without_scope_passes_none_and_clears_rejected_fields(self):
        state = {'wind': '24010', 'gust': '12'}
        scopes = []
        notifications = []

        def apply(raw):
            state['wind'] = raw.get('wind', '')
            state['gust'] = raw.get('gust', '')

        def validator(scope):
            scopes.append(scope)
            return ({'gust': ''}, ['gust_too_low'])

        pipeline = FormPipeline(
            {'wind': '24010', 'gust': '12'},
            apply=apply,
            validator=validator,
            notify=notifications.append,
        )

        errors = pipeline.validate()

        assert scopes == [None]
        assert errors == ['gust_too_low']
        assert pipeline.value('gust') == ''
        assert state['gust'] == ''
        assert notifications == ['gust_too_low']

    def test_sync_controls_derive_and_changed_emission(self):
        applyCalls = 0
        ruleCalls = []
        renderCalls = 0
        changedCalls = 0

        def apply(raw):
            nonlocal applyCalls
            applyCalls += 1

        def rules(raw, previous, changed, source):
            ruleCalls.append((set(changed), source))

        def render():
            nonlocal renderCalls
            renderCalls += 1

        def changed():
            nonlocal changedCalls
            changedCalls += 1

        pipeline = FormPipeline(
            {'wind': ''},
            apply=apply,
            rules=rules,
            render=render,
            changed=changed,
        )

        pipeline.sync({'wind': '18012'})
        assert pipeline.raw == {'wind': '18012'}
        assert pipeline.previous == {'wind': '18012'}
        assert applyCalls == 0
        assert ruleCalls == []
        assert renderCalls == 1
        assert changedCalls == 0

        pipeline.sync({'wind': '20010', 'gust': ''}, source='advisory', derive=True, changed=True)
        assert applyCalls == 1
        assert ruleCalls == [({'wind', 'gust'}, 'advisory')]
        assert renderCalls == 2
        assert changedCalls == 1

    def test_source_propagation_for_external_origins(self):
        seenSources = []

        def rules(raw, previous, changed, source):
            seenSources.append(('rules', source))

        def effect(changed, source):
            seenSources.append(('effect', source))

        pipeline = FormPipeline({}, rules=rules, effect=effect)

        for source in ('user', 'map', 'advisory', 'clock'):
            pipeline.edit({'field': source}, source=source)

        assert seenSources == [
            ('rules', 'user'),
            ('effect', 'user'),
            ('rules', 'map'),
            ('effect', 'map'),
            ('rules', 'advisory'),
            ('effect', 'advisory'),
            ('rules', 'clock'),
            ('effect', 'clock'),
        ]


class TestWidgetDiffHelpers:

    def test_set_line_text_noop_cursor_and_signals(self, qtbot):
        line = QLineEdit()
        qtbot.addWidget(line)
        line.setText('abcde')
        line.setCursorPosition(2)

        textChangedCount = 0
        textEditedCount = 0

        def onTextChanged(_):
            nonlocal textChangedCount
            textChangedCount += 1

        def onTextEdited(_):
            nonlocal textEditedCount
            textEditedCount += 1

        line.textChanged.connect(onTextChanged)
        line.textEdited.connect(onTextEdited)

        assert setLineText(line, 'abcde') is False
        assert textChangedCount == 0
        assert line.cursorPosition() == 2

        assert setLineText(line, 'ABCDE') is True
        assert line.text() == 'ABCDE'
        assert line.cursorPosition() == 2
        assert textChangedCount == 1
        assert textEditedCount == 0

        line.setCursorPosition(4)
        assert setLineText(line, 'AB/CDE') is True
        assert line.text() == 'AB/CDE'
        assert line.cursorPosition() == 5
        assert textEditedCount == 0

    def test_set_plain_text_preserves_cursor_without_text_changed(self, qtbot):
        edit = QTextEdit()
        qtbot.addWidget(edit)
        edit.setPlainText('hello')
        cursor = edit.textCursor()
        cursor.setPosition(2)
        edit.setTextCursor(cursor)

        textChangedCount = 0

        def onTextChanged():
            nonlocal textChangedCount
            textChangedCount += 1

        edit.textChanged.connect(onTextChanged)

        assert setPlainText(edit, 'hello') is False
        assert textChangedCount == 0
        assert edit.textCursor().position() == 2

        assert setPlainText(edit, 'HELLO!') is True
        assert edit.toPlainText() == 'HELLO!'
        assert edit.textCursor().position() == 3
        assert textChangedCount == 0

    def test_set_combo_options_diff_and_signals(self, qtbot):
        combo = QComboBox()
        qtbot.addWidget(combo)

        activatedCount = 0

        def onActivated(_):
            nonlocal activatedCount
            activatedCount += 1

        combo.activated.connect(onActivated)

        assert setComboOptions(combo, ['TS', 'TSGR']) is True
        assert [combo.itemText(i) for i in range(combo.count())] == ['TS', 'TSGR']
        assert setComboOptions(combo, ['TS', 'TSGR']) is False

        assert setComboOptions(combo, [('1', '100800/101200'), ('1', '101200/101600')]) is True
        assert setComboOptions(combo, [('1', '100800/101200'), ('1', '101200/101600')]) is False
        assert setComboOptions(combo, [('1', '100800/101200'), ('1', '101400/101800')]) is True
        assert combo.itemData(1) == '101400/101800'
        assert activatedCount == 0

    def test_set_combo_text_non_editable_editable_and_indexed(self, qtbot):
        combo = QComboBox()
        qtbot.addWidget(combo)
        setComboOptions(combo, [('1', 'first'), ('1', 'second'), ('2', 'third')])

        activatedCount = 0

        def onActivated(_):
            nonlocal activatedCount
            activatedCount += 1

        combo.activated.connect(onActivated)

        assert setComboText(combo, '2') is True
        assert combo.currentText() == '2'
        assert setComboText(combo, '2') is False

        assert setComboText(combo, 'missing') is True
        assert combo.currentIndex() == -1
        assert setComboText(combo, 'missing') is False

        assert setComboText(combo, '', index=1) is True
        assert combo.currentIndex() == 1
        assert combo.currentData() == 'second'
        assert setComboText(combo, '', index=1) is False
        assert activatedCount == 0

        editable = QComboBox()
        editable.setEditable(True)
        qtbot.addWidget(editable)
        editable.lineEdit().setText('ra')
        editable.lineEdit().setCursorPosition(1)

        editableActivated = 0
        editableEdited = 0

        def onEditableActivated(_):
            nonlocal editableActivated
            editableActivated += 1

        def onEditableEdited(_):
            nonlocal editableEdited
            editableEdited += 1

        editable.activated.connect(onEditableActivated)
        editable.lineEdit().textEdited.connect(onEditableEdited)

        assert setComboText(editable, 'RA') is True
        assert editable.currentText() == 'RA'
        assert editable.lineEdit().cursorPosition() == 1
        assert setComboText(editable, 'RA') is False
        assert editableActivated == 0
        assert editableEdited == 0

    def test_set_checked_diff_and_signals(self, qtbot):
        checkbox = QCheckBox()
        radio = QRadioButton()
        qtbot.addWidget(checkbox)
        qtbot.addWidget(radio)

        checkboxClicks = 0
        radioClicks = 0

        def onCheckboxClick():
            nonlocal checkboxClicks
            checkboxClicks += 1

        def onRadioClick():
            nonlocal radioClicks
            radioClicks += 1

        checkbox.clicked.connect(onCheckboxClick)
        radio.clicked.connect(onRadioClick)

        assert setChecked(checkbox, False) is False
        assert setChecked(checkbox, True) is True
        assert checkbox.isChecked() is True
        assert setChecked(checkbox, True) is False

        assert setChecked(radio, False) is False
        assert setChecked(radio, True) is True
        assert radio.isChecked() is True
        assert checkboxClicks == 0
        assert radioClicks == 0
