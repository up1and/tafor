import json

from tafor.core.models import Base, Metar, Other, MessageMixin, Sigmet, Taf, Trend

DECLARED_INDEXES = {
    'ix_metars_created',
    'ix_tafs_type_created',
    'ix_tafs_created',
    'ix_sigmets_type_created',
}


class TestDeclaredIndexes:

    def test_metadata_declares_indexes(self):
        names = {i.name for table in Base.metadata.tables.values() for i in table.indexes}
        assert DECLARED_INDEXES <= names


class TestMessageMixin:

    """rawText/isCnl used to be copy-pasted into all five models.

    They now share MessageMixin, so this pins the behaviour down once.
    """

    def test_aftn_payload_is_rejoined_with_four_blank_lines(self):
        message = Taf(text='TAF ZSSS 120000Z', protocol='aftn',
                       raw=json.dumps(['PART1', 'PART2']))

        separator = (chr(13) + chr(10)) * 4
        assert message.rawText() == 'PART1' + separator + 'PART2'

    def test_non_aftn_payload_is_returned_as_is(self):
        message = Taf(text='TAF ZSSS 120000Z', protocol='ftp', raw='PLAIN TEXT')

        assert message.rawText() == 'PLAIN TEXT'

    def test_missing_payload_reads_as_empty(self):
        assert Taf(text='TAF', protocol='ftp', raw=None).rawText() == ''
        assert Taf(text='TAF', protocol='ftp', raw='').rawText() == ''

    def test_is_cnl_detects_the_cancel_token(self):
        assert Taf(text='TAF ZSSS CNL ABC', protocol='ftp').isCnl() is True
        assert Taf(text='TAF ZSSS 120000Z', protocol='ftp').isCnl() is False

    def test_every_message_model_shares_the_mixin(self):
        for cls in [Taf, Metar, Trend, Sigmet, Other]:
            assert issubclass(cls, MessageMixin), cls.__name__
