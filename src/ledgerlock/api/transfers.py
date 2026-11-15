from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from ledgerlock.db.session import get_db
from ledgerlock.schemas.transfer import TransferRequest, TransferResponse
from ledgerlock.services.transfer_service import (
    AccountNotFound,
    IdempotencyConflict,
    InsufficientFunds,
    transfer_funds,
)

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: TransferRequest,
    response: Response,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    db: Session = Depends(get_db),
) -> TransferResponse:
    try:
        result, replayed = transfer_funds(db, payload, idempotency_key)
    except AccountNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InsufficientFunds as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if replayed:
        response.status_code = status.HTTP_200_OK
    return result
