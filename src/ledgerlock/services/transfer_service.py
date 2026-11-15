import hashlib
import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ledgerlock.models import Account, IdempotencyKey, LedgerEntry
from ledgerlock.schemas.transfer import TransferRequest, TransferResponse


class TransferError(Exception):
    pass


class AccountNotFound(TransferError):
    pass


class InsufficientFunds(TransferError):
    pass


class IdempotencyConflict(TransferError):
    pass


def transfer_funds(
    db: Session, request: TransferRequest, idempotency_key: str
) -> tuple[TransferResponse, bool]:
    request_data = request.model_dump(mode="json")
    request_hash = hashlib.sha256(
        json.dumps(request_data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    try:
        with db.begin():
            existing = db.get(IdempotencyKey, idempotency_key)
            if existing is not None:
                return _existing_response(existing, request_hash), True

            account_ids = sorted(
                [request.source_account_id, request.destination_account_id]
            )
            accounts = db.scalars(
                select(Account)
                .where(Account.id.in_(account_ids))
                .order_by(Account.id)
                .with_for_update()
            ).all()
            by_id = {account.id: account for account in accounts}
            if len(by_id) != 2:
                raise AccountNotFound("Both accounts must exist")

            source = by_id[request.source_account_id]
            destination = by_id[request.destination_account_id]
            if source.balance < request.amount:
                raise InsufficientFunds("Insufficient funds")

            transfer_id = str(uuid4())
            key_record = IdempotencyKey(
                key=idempotency_key,
                request_hash=request_hash,
                transfer_id=transfer_id,
                source_account_id=request.source_account_id,
                destination_account_id=request.destination_account_id,
                amount=request.amount,
            )
            db.add(key_record)
            db.flush()

            source.balance -= request.amount
            destination.balance += request.amount
            db.add_all(
                [
                    LedgerEntry(
                        transfer_id=transfer_id,
                        account_id=source.id,
                        amount=-request.amount,
                    ),
                    LedgerEntry(
                        transfer_id=transfer_id,
                        account_id=destination.id,
                        amount=request.amount,
                    ),
                ]
            )
            response = _response(key_record)
        return response, False
    except IntegrityError:
        db.rollback()
        existing = db.get(IdempotencyKey, idempotency_key)
        if existing is None:
            raise
        return _existing_response(existing, request_hash), True


def _existing_response(
    existing: IdempotencyKey, request_hash: str
) -> TransferResponse:
    if existing.request_hash != request_hash:
        raise IdempotencyConflict("Idempotency key was already used for another request")
    return _response(existing)


def _response(key: IdempotencyKey) -> TransferResponse:
    return TransferResponse(
        transfer_id=key.transfer_id,
        source_account_id=key.source_account_id,
        destination_account_id=key.destination_account_id,
        amount=key.amount,
    )
