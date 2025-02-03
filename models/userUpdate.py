from pydantic import BaseModel


class UserUpdate(BaseModel):
    # user_id: int
    username: str
    new_username: str
    new_password: str