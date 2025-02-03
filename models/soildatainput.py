from pydantic import BaseModel


class SoilDataInput(BaseModel):
    nitrogen: float
    phosphorus: float
    potassium: float
    ph: float
    humidity: float
    temperature: float