from pydantic import BaseModel, EmailStr


class UserSignup(BaseModel):
    email: EmailStr
    username: str
    password: str