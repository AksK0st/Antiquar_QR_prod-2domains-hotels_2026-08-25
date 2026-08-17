import asyncio
from getpass import getpass

from sqlalchemy import delete, select

from db import SessionLocal
from models.admin_session import AdminSession
from models.admin_user import AdminUser
from security.passwords import hash_password


MIN_PASSWORD_LENGTH = 14
MAX_PASSWORD_LENGTH = 256


async def reset_admin_password() -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            select(AdminUser)
            .order_by(AdminUser.id)
            .limit(2)
        )

        admins = result.scalars().all()

        if not admins:
            print("Admin user does not exist.")
            return

        if len(admins) > 1:
            print("Multiple admin users found. Aborting.")
            return

        admin = admins[0]

        password = getpass("New password: ")
        password_repeat = getpass("Repeat new password: ")

        if password != password_repeat:
            print("Passwords do not match.")
            return

        if len(password) < MIN_PASSWORD_LENGTH:
            print(
                f"Password must contain at least "
                f"{MIN_PASSWORD_LENGTH} characters."
            )
            return

        if len(password) > MAX_PASSWORD_LENGTH:
            print(
                f"Password must contain at most "
                f"{MAX_PASSWORD_LENGTH} characters."
            )
            return

        admin.password_hash = hash_password(password)

        await db.execute(
            delete(AdminSession).where(
                AdminSession.admin_id == admin.id
            )
        )

        await db.commit()

        print(
            f"Password for admin '{admin.username}' "
            f"was reset successfully."
        )
        print("All admin sessions were revoked.")


if __name__ == "__main__":
    asyncio.run(reset_admin_password())