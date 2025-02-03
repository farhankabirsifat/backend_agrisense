from pydantic import BaseModel


class DeleteUserRequest(BaseModel):
    # identifier: str
    username: str
    # email: str
