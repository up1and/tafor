import datetime
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


class TestSigmetExpired:
    """A SIGMET without a VALID group has no validity window; reading one
    must not crash and must read as never expiring."""

    NO_VALID = ('ZJSA SANYA FIR OBSC TS FCST WI E11223 N1829 - '
                'E11142 N1916 TOP FL030 MOV N 300KMH NC=')
    WITH_VALID = ('VALID 100730/101430 ZJHK- ZJSA SANYA FIR OBSC TS FCST '
                  'WI E11223 N1829 - E11142 N1916 TOP FL030 MOV N 300KMH NC=')

    def test_expired_returns_none_without_valid_group(self):
        sig = Sigmet(type='WS', text=self.NO_VALID)
        assert sig.expired() is None

    def test_expired_reads_the_ending_time(self):
        sig = Sigmet(type='WS', text=self.WITH_VALID,
                     created=datetime.datetime(2026, 10, 10, 7, 0))
        ending = sig.expired()
        assert (ending.day, ending.hour) == (10, 14)

    def test_missing_validity_reads_as_not_expired(self):
        sig = Sigmet(type='WS', text=self.NO_VALID)
        assert sig.isExpired() is False
