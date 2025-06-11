from pydantic import ConfigDict, BaseModel, Field

from model.user import User


# модель чтения пользователя из БД
class Read_User(BaseModel):
    # id: int
    model_config = ConfigDict(from_attribures=True)

# модель аунтентификации
class SUserAuth(BaseModel):
    login: str = Field(..., description="Имя пользователя")
    password: str = Field(..., min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")