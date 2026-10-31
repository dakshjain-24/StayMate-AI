from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import delete, select, text

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (
    Booking,
    BookingStatus,
    Guest,
    Hotel,
    KnowledgeChunk,
    RequestType,
    Room,
    RoomStatus,
    ServiceRequest,
)
from app.services.rag_service import add_knowledge_chunks


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "knowledge"


def chunk_text(
    text: str,
    max_chars: int = 550,
    overlap_chars: int = 80,
) -> list[str]:
    """
    Split markdown text into reasonably sized chunks.

    Paragraph boundaries are preferred, while very large
    paragraphs are split further.
    """

    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:

        # Split unusually large paragraphs.
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""

            start = 0

            while start < len(paragraph):
                end = start + max_chars

                chunk = paragraph[start:end].strip()

                if chunk:
                    chunks.append(chunk)

                start += max_chars - overlap_chars

            continue

        candidate = (
            f"{current}\n\n{paragraph}".strip()
            if current
            else paragraph
        )

        if len(candidate) <= max_chars:
            current = candidate

        else:
            if current:
                chunks.append(current)

            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def seed():
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE EXTENSION IF NOT EXISTS vector"
            )
        )

    Base.metadata.create_all(
        bind=engine
    )

    with SessionLocal() as db:

        # -------------------------
        # Hotel
        # -------------------------

        hotel = db.get(
            Hotel,
            1,
        )

        if not hotel:
            hotel = Hotel(
                id=1,
                name="StayMate Grand",
                city="Varanasi",
            )

            db.add(hotel)
            db.flush()

        # -------------------------
        # Rooms
        # -------------------------

        existing_rooms = db.scalar(
            select(Room.id)
            .where(
                Room.hotel_id == 1
            )
            .limit(1)
        )

        if not existing_rooms:
            rooms = [
                Room(
                    hotel_id=1,
                    number="201",
                    room_type="standard",
                    price_per_night=3200,
                    status=RoomStatus.available,
                ),
                Room(
                    hotel_id=1,
                    number="202",
                    room_type="standard",
                    price_per_night=3200,
                    status=RoomStatus.available,
                ),
                Room(
                    hotel_id=1,
                    number="203",
                    room_type="standard",
                    price_per_night=3400,
                    status=RoomStatus.cleaning,
                ),
                Room(
                    hotel_id=1,
                    number="301",
                    room_type="deluxe",
                    price_per_night=4800,
                    status=RoomStatus.available,
                ),
                Room(
                    hotel_id=1,
                    number="302",
                    room_type="deluxe",
                    price_per_night=4800,
                    status=RoomStatus.available,
                ),
                Room(
                    hotel_id=1,
                    number="303",
                    room_type="deluxe",
                    price_per_night=5200,
                    status=RoomStatus.available,
                ),
                Room(
                    hotel_id=1,
                    number="401",
                    room_type="suite",
                    price_per_night=7600,
                    status=RoomStatus.available,
                ),
                Room(
                    hotel_id=1,
                    number="402",
                    room_type="suite",
                    price_per_night=8200,
                    status=RoomStatus.maintenance,
                ),
            ]

            db.add_all(rooms)
            db.commit()

        # -------------------------
        # Demo guest
        # -------------------------

        guest = db.scalar(
            select(Guest)
            .where(
                Guest.email
                == "demo@staymate.dev"
            )
        )

        if not guest:
            guest = Guest(
                name="Demo Guest",
                email="demo@staymate.dev",
                phone="+91 90000 00000",
            )

            db.add(guest)
            db.flush()

            room = db.scalar(
                select(Room)
                .where(
                    Room.number == "301",
                    Room.hotel_id == 1,
                )
            )

            booking = Booking(
                hotel_id=1,
                guest_id=guest.id,
                room_id=room.id,
                check_in=date.today()
                + timedelta(days=2),
                check_out=date.today()
                + timedelta(days=5),
                status=BookingStatus.confirmed,
                total_amount=14400,
            )

            request = ServiceRequest(
                hotel_id=1,
                room_id=room.id,
                guest_id=guest.id,
                request_type=RequestType.housekeeping,
                description=(
                    "Please send two extra towels "
                    "in the evening."
                ),
            )

            db.add_all(
                [
                    booking,
                    request,
                ]
            )

            db.commit()

        # -------------------------
        # Knowledge base
        # -------------------------

        db.execute(
            delete(KnowledgeChunk)
            .where(
                KnowledgeChunk.hotel_id == 1
            )
        )

        db.commit()

        knowledge_files = sorted(
            KNOWLEDGE_DIR.glob("*.md")
        )

        if not knowledge_files:
            print(
                "No markdown files found in knowledge folder."
            )
            return

        total_chunks = 0

        for path in knowledge_files:

            text_content = path.read_text(
                encoding="utf-8"
            )

            chunks = chunk_text(
                text_content
            )

            add_knowledge_chunks(
                db,
                hotel_id=1,
                source=path.name,
                chunks=chunks,
            )

            total_chunks += len(chunks)

            print(
                f"Indexed {len(chunks)} chunks "
                f"from {path.name}"
            )

        print()
        print(
            f"Total knowledge chunks indexed: "
            f"{total_chunks}"
        )

    print("Seed complete.")


if __name__ == "__main__":
    seed()