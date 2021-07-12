from rotkehlchen.db.ledger_actions import DBLedgerActions, GitcoinGrantMetadata


def test_gitcoin_metadata(database):
    db = DBLedgerActions(database, database.msg_aggregator)
    db.set_gitcoin_grant_metadata(
        grant_id=1, name='foo', created_on=1,
    )
    result = db.get_gitcoin_grant_metadata(1)
    assert result == {1: GitcoinGrantMetadata(grant_id=1, name='foo', created_on=1)}

    # change existing grant metadata
    db.set_gitcoin_grant_metadata(
        grant_id=1, name='newfoo', created_on=2,
    )
    result = db.get_gitcoin_grant_metadata(1)
    assert result == {1: GitcoinGrantMetadata(grant_id=1, name='newfoo', created_on=2)}

    # add 2nd grant and check we can get both back
    db.set_gitcoin_grant_metadata(
        grant_id=2, name='boo', created_on=3,
    )
    result = db.get_gitcoin_grant_metadata(2)
    assert result == {2: GitcoinGrantMetadata(grant_id=2, name='boo', created_on=3)}
    assert db.get_gitcoin_grant_metadata() == {
        1: GitcoinGrantMetadata(grant_id=1, name='newfoo', created_on=2),
        2: GitcoinGrantMetadata(grant_id=2, name='boo', created_on=3),
    }
