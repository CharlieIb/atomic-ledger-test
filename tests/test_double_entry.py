from decimal import Decimal

from ledgerlock.models import LedgerEntry


def test_each_transfer_has_balanced_debit_and_credit(client, database):
    response = client.post(
        "/transfers",
        headers={"Idempotency-Key": "balanced"},
        json={
            "source_account_id": 1,
            "destination_account_id": 2,
            "amount": "30.00",
        },
    )
    assert response.status_code == 201

    session, _ = database
    transfer_id = response.json()["transfer_id"]
    entries = (
        session.query(LedgerEntry)
        .filter(LedgerEntry.transfer_id == transfer_id)
        .all()
    )
    assert len(entries) == 2
    assert sum((entry.amount for entry in entries), Decimal("0.00")) == Decimal("0.00")
    assert {entry.amount for entry in entries} == {
        Decimal("-30.00"),
        Decimal("30.00"),
    }
