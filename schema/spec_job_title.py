from pydantic import BaseModel

class SpecJobTitleResponse(BaseModel):
    name: str
    description: str