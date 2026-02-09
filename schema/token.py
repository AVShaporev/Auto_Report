from pydantic import ConfigDict, BaseModel, Field, EmailStr


# schemas/token.py
class Token(BaseModel):
    username: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str  # user_id или username
    exp: int
    type: str  # access или refresh