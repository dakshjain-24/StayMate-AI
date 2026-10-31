from sqlalchemy import select
from sqlalchemy.orm import Session

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings
from app.models import KnowledgeChunk


_embeddings: GoogleGenerativeAIEmbeddings | None = None


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    global _embeddings

    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            api_key=settings.gemini_api_key,
            output_dimensionality=1536,
        )

    return _embeddings


def search_knowledge(db: Session, query: str, hotel_id: int, limit: int = 4) -> list[KnowledgeChunk]:
    vector = get_embeddings().embed_query(query)
    stmt = (
        select(KnowledgeChunk)
        .where(KnowledgeChunk.hotel_id == hotel_id)
        .order_by(KnowledgeChunk.embedding.cosine_distance(vector))
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def add_knowledge_chunks(db: Session, hotel_id: int, source: str, chunks: list[str]) -> int:
    embedder = get_embeddings()
    vectors = embedder.embed_documents(chunks)

    rows = [
        KnowledgeChunk(hotel_id=hotel_id, source=source, content=text, embedding=vector)
        for text, vector in zip(chunks, vectors, strict=True)
    ]
    db.add_all(rows)
    db.commit()
    return len(rows)
