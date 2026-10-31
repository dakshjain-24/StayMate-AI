from getpass import getpass

from sqlalchemy import (
    func,
    select,
)

import app.models

from app.db.base import Base
from app.db.session import (
    SessionLocal,
    engine,
)

from app.models import (
    Hotel,
    StaffUser,
)

from app.services.auth_service import (
    hash_password,
)


def main():

    Base.metadata.create_all(
        bind=engine
    )

    print()
    print(
        "StayMate Staff Account"
    )
    print(
        "----------------------"
    )

    name = input(
        "Staff name: "
    ).strip()

    email = input(
        "Staff email: "
    ).strip().lower()

    hotel_input = input(
        "Hotel ID [1]: "
    ).strip()

    hotel_id = (
        int(hotel_input)
        if hotel_input
        else 1
    )

    password = getpass(
        "Password: "
    )

    confirm_password = getpass(
        "Confirm password: "
    )

    if password != confirm_password:

        print(
            "Passwords do not match."
        )

        return

    if len(password) < 10:

        print(
            "Use a password with at least "
            "10 characters."
        )

        return

    with SessionLocal() as db:

        hotel = db.get(
            Hotel,
            hotel_id,
        )

        if not hotel:

            print(
                f"Hotel {hotel_id} "
                "does not exist."
            )

            return

        staff = db.scalar(
            select(
                StaffUser
            ).where(
                func.lower(
                    StaffUser.email
                )
                == email
            )
        )

        password_hash = (
            hash_password(
                password
            )
        )

        if staff:

            staff.name = name
            staff.hotel_id = hotel_id
            staff.password_hash = (
                password_hash
            )
            staff.is_active = True

            db.commit()

            print()
            print(
                "Existing staff account "
                "updated successfully."
            )

            return

        staff = StaffUser(
            hotel_id=hotel_id,
            name=name,
            email=email,
            password_hash=
                password_hash,
            is_active=True,
        )

        db.add(
            staff
        )

        db.commit()

        print()
        print(
            "Staff account created "
            "successfully."
        )


if __name__ == "__main__":
    main()