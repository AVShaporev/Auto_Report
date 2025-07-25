from pydantic import BaseModel

class SpecContractResponse(BaseModel):
    name: str
    description: str