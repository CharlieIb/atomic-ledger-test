from decimal import Decimal

from ledgerlock.models import Account, LedgerEntry


def test_transfer_updates_balances_and_returns_created(client, database):
    response = client.post(
        "/transfers",
        headers={"Idempotency-Key": "transfer-1"},
        json={
            "source_account_id": 1,
            "destination_account_id": 2,
            "amount": "12.50",
        },
    )

    assert response.status_code == 201
    assert response.json()["amount"] == "12.50"
    session, _ = database
    assert session.get(Account, 1).balance == Decimal("87.50")
    assert session.get(Account, 2).balance == Decimal("37.50")
    entries = session.query(LedgerEntry).all()
    assert sorted(entry.amount for entry in entries) == [
        Decimal("-12.50"),
        Decimal("12.50"),
    ]


def test_transfer_rejects_invalid_amount_and_same_account(client):
    negative = client.post(
        "/transfers",
        headers={"Idempotency-Key": "negative"},
        json={
            "source_account_id": 1,
            "destination_account_id": 2,
            "amount": "-1",
        },
    )
    same_account = client.post(
        "/transfers",
        headers={"Idempotency-Key": "same"},
        json={
            "source_account_id": 1,
            "destination_account_id": 1,
            "amount": "1",
        },
    )

    assert negative.status_code == 422
    assert same_account.status_code == 422


def test_transfer_rejects_missing_account_and_insufficient_funds(client):
    missing = client.post(
        "/transfers",
        headers={"Idempotency-Key": "missing"},
        json={
            "source_account_id": 1,
            "destination_account_id": 99,
            "amount": "1",
        },
    )
    insufficient = client.post(
        "/transfers",
        headers={"Idempotency-Key": "insufficient"},
        json={
            "source_account_id": 1,
            "destination_account_id": 2,
            "amount": "100.01",
        },
    )

    assert missing.status_code == 404
    assert insufficient.status_code == 409
