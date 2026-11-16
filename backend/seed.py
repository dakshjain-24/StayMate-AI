from datetime import date, timedelta
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from sqlalchemy import delete, select, text
from langchain_community.document_loaders import DirectoryLoader, TextLoader

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

def chunk_text(text: str, max_chars: int = 550, overlap_chars: int = 80) -> list[str]:
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.MARKDOWN,
        chunk_size=max_chars,
        chunk_overlap=overlap_chars,
    )


    chunks = splitter.split_text(text)

    return chunks


def seed():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:


        # Hotel

        hotel = db.get(Hotel, 1)

        if not hotel:
            hotel = Hotel(id=1, name="StayMate Grand", city="Varanasi")
            db.add(hotel)
            db.flush()


        # Rooms

        existing_rooms = db.scalar(select(Room.id).where(Room.hotel_id == 1).limit(1))

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


        # Demo guest

        guest = db.scalar(select(Guest).where(Guest.email == "demo@staymate.dev"))

        if not guest:
            guest = Guest(
                name="Demo Guest",
                email="demo@staymate.dev",
                phone="+91 90000 00000"
            )

            db.add(guest)
            db.flush()

            room = db.scalar(select(Room).where(Room.number == "301", Room.hotel_id == 1))

            booking = Booking(
                hotel_id=1,
                guest_id=guest.id,
                room_id=room.id,
                check_in=date.today() + timedelta(days=2),
                check_out=date.today() + timedelta(days=5),
                status=BookingStatus.confirmed,
                total_amount=14400,
            )

            request = ServiceRequest(
                hotel_id=1,
                room_id=room.id,
                guest_id=guest.id,
                request_type=RequestType.housekeeping,
                description=("Please send two extra towels in the evening.")
            )

            db.add_all([booking, request])
            db.commit()


        # Knowledge base

        db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.hotel_id == 1))
        db.commit()


        loader = DirectoryLoader(
            str(KNOWLEDGE_DIR),
            glob="*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
            show_progress=True
        )

        documents = loader.load()

        if not documents:
            print("No markdown files found in knowledge folder.")
            return

        total_chunks = 0

        for doc in documents:

            source = Path(doc.metadata["source"]).name

            text_content = doc.page_content

            chunks = chunk_text(text_content)

            add_knowledge_chunks(db,hotel_id=1,source=source,chunks=chunks)

            total_chunks += len(chunks)

            print(f"Indexed {len(chunks)} chunks from {source}")

        print()
        print(f"Total knowledge chunks indexed: {total_chunks}")

    print("Seed complete.")


if __name__ == "__main__":
    seed()