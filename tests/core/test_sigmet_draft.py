"""Tests for tafor/core/sigmet/draft.py, mirroring test_taf_draft.py."""

from tafor.core.sigmet import SigmetDraft


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
