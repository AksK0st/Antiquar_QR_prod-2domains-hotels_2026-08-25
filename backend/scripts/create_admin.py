import asyncio
from getpass import getpass

from sqlalchemy import func, select
from db import SessionLocal
from models.admin_user import AdminUser
from security.passwords import hash_password


MIN_PASSWORD_LENGTH = 14


async def create_admin() -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            select(func.count(AdminUser.id))
        )
        admin_count = result.scalar_one()

        if admin_count > 0:
            print("Admin user already exists.")
            print("Only one administrator is allowed.")
            return

        username = input("Username: ").strip()

        if not username:
            print("Username cannot be empty.")
            return

        password = getpass("Password: ")
        password_repeat = getpass("Repeat password: ")

        if password != password_repeat:
            print("Passwords do not match.")
            return

        if len(password) < MIN_PASSWORD_LENGTH:
            print(
                f"Password must contain at least "
                f"{MIN_PASSWORD_LENGTH} characters."
            )
            return

        admin = AdminUser(
            username=username,
            password_hash=hash_password(password),
        )

        db.add(admin)
        await db.commit()

        print(f"Admin '{username}' created successfully.")


if __name__ == "__main__":
    asyncio.run(create_admin())