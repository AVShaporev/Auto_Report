from pydantic import BaseModel

class BankResponse(BaseModel):
    name: str
    bik: str
    inn: str
    description: str