from decimal import Decimal

from ledgerlock.models import Account, LedgerEntry


def test_same_key_replays_original_transfer(client, database):
    payload = {
        "source_account_id": 1,
        "destination_account_id": 2,
        "amount": "12.50",
    }
    first = client.post(
        "/transfers", headers={"Idempotency-Key": "repeat"}, json=payload
    )
    second = client.post(
        "/transfers", headers={"Idempotency-Key": "repeat"}, json=payload
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json() == second.json()
    session, _ = database
    assert session.get(Account, 1).balance == Decimal("87.50")
    assert session.query(LedgerEntry).count() == 2


def test_same_key_with_different_payload_conflicts(client, database):
    headers = {"Idempotency-Key": "reused"}
    client.post(
        "/transfers",
        headers=headers,
        json={
            "source_account_id": 1,
            "destination_account_id": 2,
            "amount": "12.50",
        },
    )
    response = client.post(
        "/transfers",
        headers=headers,
        json={
            "source_account_id": 1,
            "destination_account_id": 2,
            "amount": "15.00",
        },
    )

    assert response.status_code == 409
    session, _ = database
    assert session.get(Account, 1).balance == Decimal("87.50")
