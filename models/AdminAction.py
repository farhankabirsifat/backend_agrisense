from pydantic import BaseModel, EmailStr


class AdminAction(BaseModel):
    admin_email: EmailStr
    # target_user_id: int
    username: str