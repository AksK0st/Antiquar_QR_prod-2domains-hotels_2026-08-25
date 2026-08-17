#Просто проверка хэша пароля в отдельном модуле
import secrets

from pwdlib import PasswordHash


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)

_dummy_password_hash = password_hasher.hash(
    secrets.token_urlsafe(32)
)



def verify_password(
    plain_password: str,
    password_hash: str,
) -> bool:
    return password_hasher.verify(
        plain_password,
        password_hash,
    )

def verify_password_or_dummy(
    plain_password: str,
    password_hash: str | None,
) -> bool:
    hash_to_check = (
        password_hash
        if password_hash is not None
        else _dummy_password_hash
    )

    is_valid = password_hasher.verify(
        plain_password,
        hash_to_check,
    )

    return password_hash is not None and is_valid