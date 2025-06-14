from datetime import date

from pydantic import ConfigDict, BaseModel
from sqlalchemy.orm import Mapped

from model.organization import Organization


class Read_Contract(BaseModel):
    # id: int
    # model_config = ConfigDict(from_attribures=True)
    number: str
    # date_of_consclusion: Mapped[date]
    # subject: str
    # customer: Mapped[Organization]
    # exeсutor: Mapped[Organization]
    # date_of_completion: Mapped[date]

