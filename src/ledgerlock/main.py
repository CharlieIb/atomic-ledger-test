from fastapi import FastAPI

from ledgerlock.api.transfers import router as transfers_router

app = FastAPI(title="LedgerLock", version="0.1.0")
app.include_router(transfers_router)
