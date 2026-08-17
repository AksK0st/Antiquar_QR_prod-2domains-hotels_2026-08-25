from pydantic import BaseModel, Field, SecretStr


class AdminLoginRequest(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=100,
    )

    password: SecretStr = Field(
        min_length=1,
        max_length=256,
    )


class AdminLoginResponse(BaseModel):
    authenticated: bool
    username: str