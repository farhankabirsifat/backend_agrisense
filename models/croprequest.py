from pydantic import BaseModel


class CropRequest(BaseModel):
    crop_name: str