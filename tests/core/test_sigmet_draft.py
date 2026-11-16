"""Tests for tafor/core/sigmet/draft.py, mirroring test_taf_draft.py."""

import datetime

from tafor.core.sigmet import SigmetDraft
from tafor.core.sigmet.states import SigmetCustomState, SigmetGeneralState

MOMENT = datetime.datetime(2026, 6, 10, 9, 30)


def draft(form='general'):
    d = SigmetDraft()
    if form != 'general':
        d.select(form)
    return d


class TestFormSelection:

    def test_starts_on_the_general_product(self):
        d = draft()
        assert d.form == 'general'
        assert d.designator == 'WS'

    def test_selecting_a_product_form_sets_its_designator(self):
        # starts from cancel so every product form is a real change, and
        # leaving cancel takes the new form's product, not a remembered one
        for form, designator in SigmetDraft.products.items():
            d = draft(form='cancel')
            assert d.select(form) is True
            assert d.form == form
            assert d.designator == designator

    def test_selecting_the_current_form_changes_nothing(self):
        d = draft()
        assert d.select('general') is False
        assert d.form == 'general'
        assert d.designator == 'WS'

    def test_cancel_keeps_the_selected_product(self):
        d = draft(form='typhoon')
        assert d.select('cancel') is True
        assert d.form == 'cancel'
        assert d.designator == 'WC'

    def test_custom_keeps_the_selected_product(self):
        d = draft(form='ash')
        assert d.select('custom') is True
        assert d.form == 'custom'
        assert d.designator == 'WV'


class TestDerivedValues:

    def test_span_follows_the_designator(self):
        for form, hours in [('general', 4), ('typhoon', 6), ('ash', 6), ('airmet', 4)]:
            assert draft(form=form).span() == hours

    def test_category_follows_the_designator(self):
        assert draft(form='airmet').category() == 'AIRMET'
        assert draft(form='typhoon').category() == 'SIGMET'
        assert draft().category() == 'SIGMET'

    def test_the_product_forms_carry_a_sketch(self):
        for form in SigmetDraft.products:
            assert draft(form=form).hasSketch() is True

    def test_cancel_and_custom_carry_no_sketch(self):
        assert draft(form='cancel').hasSketch() is False
        assert draft(form='custom').hasSketch() is False


class TestCompose:
    """The draft answers what it is and whether it could go; the canvas is the
    editor's half of the second question, not the draft's."""

    def document(self, form='general'):
        d = SigmetDraft(fir='YUDD SHANLON FIR', airport='ZJHK', bulletinNumber='2',
                        now=lambda: MOMENT)
        d.select(form)
        for name, value in [('area', 'ZJSA'), ('sign', 'SIGMET'), ('sequence', '2'),
                            ('beginningTime', '100930'), ('endingTime', '101430'),
                            ('icao', 'ZJHK')]:
            setattr(d.header, name, value)
        return d

    def test_the_heading_comes_from_the_drafts_own_facts(self):
        d = self.document('custom')
        state = SigmetCustomState(d.header)
        state.text = 'OBSC TS'
        d.attach(state)

        message = d.compose()

        assert message.type == 'WS'
        assert message.heading == 'WS2 ZJHK 100930'
        assert message.text == 'ZJSA SIGMET 2 VALID 100930/101430 ZJHK-\nYUDD SHANLON FIR OBSC TS='

    def test_a_sketch_location_reaches_the_body(self):
        d = self.document()
        state = SigmetGeneralState('KMH', d.header)
        state.description = 'SEV'
        state.phenomenon = 'TS'
        d.attach(state)

        assert 'N2000 E11000' in d.compose({'location': 'N2000 E11000'}).text

    def test_a_body_without_a_sketch_composes_with_no_locations(self):
        d = self.document('custom')
        state = SigmetCustomState(d.header)
        state.text = 'OBSC TS'
        d.attach(state)

        assert d.compose().text.endswith('OBSC TS=')


class TestAcceptability:

    def test_a_draft_without_a_body_is_not_acceptable(self):
        assert SigmetDraft().isAcceptable() is False

    def test_the_attached_body_decides(self):
        d = TestCompose().document('custom')
        state = SigmetCustomState(d.header)
        d.attach(state)

        assert d.isAcceptable() is False

        state.text = 'OBSC TS'
        assert d.isAcceptable() is True
