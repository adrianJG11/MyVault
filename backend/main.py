from fastapi import FastAPI

from accounts.router import router as accounts_router
from investments.router import router as investments_router
from transactions.router import router as transactions_router

app = FastAPI()
app.include_router(accounts_router)
app.include_router(transactions_router)
app.include_router(investments_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
