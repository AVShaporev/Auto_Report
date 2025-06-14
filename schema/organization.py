from pydantic import ConfigDict, BaseModel


class Read_Organization(BaseModel):
    # id: int
    # model_config = ConfigDict(from_attribures=True)
    name: str
