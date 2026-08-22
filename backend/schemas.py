from pydantic import BaseModel


class ImportResult(BaseModel):
    imported: int
