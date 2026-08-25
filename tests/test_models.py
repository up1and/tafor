from tafor.core.models import Base

DECLARED_INDEXES = {
    'ix_metars_created',
    'ix_tafs_type_created',
    'ix_tafs_created',
    'ix_sigmets_type_created',
}


class TestDeclaredIndexes(object):

    def test_metadata_declares_indexes(self):
        names = {i.name for table in Base.metadata.tables.values() for i in table.indexes}
        assert DECLARED_INDEXES <= names
