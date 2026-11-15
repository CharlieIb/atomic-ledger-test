from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TransferRequest(BaseModel):
    source_account_id: int = Field(gt=0)
    destination_account_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)

    @model_validator(mode="after")
    def validate_distinct_accounts(self):
        if self.source_account_id == self.destination_account_id:
            raise ValueError("Source and destination accounts must be different")
        return self


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transfer_id: str
    source_account_id: int
    destination_account_id: int
    amount: Decimal
