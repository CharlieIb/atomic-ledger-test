import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ledgerlock.models import Account, IdempotencyKey, LedgerEntry
from ledgerlock.schemas.transfer import TransferRequest
from ledgerlock.services.transfer_service import InsufficientFunds, transfer_funds


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="PostgreSQL is required to exercise row-level transfer locking",
)
def test_concurrent_transfers_do_not_overdraw():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        session.add_all(
            [
                Account(id=91001, name="Concurrent source", balance=100),
                Account(id=91002, name="Concurrent destination", balance=0),
            ]
        )

    def send(key):
        with factory() as session:
            try:
                transfer_funds(
                    session,
                    TransferRequest(
                        source_account_id=91001,
                        destination_account_id=91002,
                        amount=Decimal("75.00"),
                    ),
                    key,
                )
                return "completed"
            except InsufficientFunds:
                return "rejected"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(send, ("concurrent-a", "concurrent-b")))
        with factory() as session:
            assert sorted(results) == ["completed", "rejected"]
            assert session.get(Account, 91001).balance == Decimal("25.00")
            assert session.get(Account, 91002).balance == Decimal("75.00")
    finally:
        with factory.begin() as session:
            session.query(LedgerEntry).filter(
                LedgerEntry.account_id.in_([91001, 91002])
            ).delete(synchronize_session=False)
            session.query(IdempotencyKey).filter(
                IdempotencyKey.source_account_id.in_([91001, 91002])
                | IdempotencyKey.destination_account_id.in_([91001, 91002])
            ).delete(synchronize_session=False)
            session.query(Account).filter(Account.id.in_([91001, 91002])).delete(
                synchronize_session=False
            )
        engine.dispose()
