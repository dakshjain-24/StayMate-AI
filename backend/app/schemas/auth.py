from pydantic import BaseModel, EmailStr, Field

class StaffLoginRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


class StaffIdentity(BaseModel):
    id: int
    name: str
    email: str
    hotel_id: int


class StaffLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff: StaffIdentity