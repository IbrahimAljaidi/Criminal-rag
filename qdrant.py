import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)

load_dotenv()


# Qdrant connection settings
qdrant_url = os.getenv("QDRANT_URL")
qdrant_api = os.getenv("QDRANT_API_KEY")
collection = os.getenv("QDRANT_COLLECTION")


# Connect to Qdrant
client = QdrantClient(
    url=qdrant_url,
    api_key=qdrant_api
)


# ==========================================
# Save chunks and vectors
# ==========================================

def save_chunks(chunks, vectors):

    points = []

    # Connect each chunk with its vector
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):

        point = PointStruct(
            id=i,
            vector=vector,
            payload={
                "chunk_id": i,
                "article_number": chunk["article_number"],
                "article_title": chunk["article_title"],
                "source_type": chunk["source_type"],
                "text": chunk["text"]
            }
        )

        points.append(point)

    # Number of points sent in each request
    batch_size = 50

    # Send points to Qdrant in smaller batches
    for i in range(0, len(points), batch_size):

        batch = points[i:i + batch_size]

        print(
            f"Saving points "
            f"{i + 1}-{min(i + batch_size, len(points))} "
            f"of {len(points)}"
        )

        client.upsert(
            collection_name=collection,
            points=batch
        )


# ==========================================
# Semantic search
# ==========================================

def search_chunks(query_vector, limit=10):

    result = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=limit
    )

    return result.points


# ==========================================
# Exact article search
# ==========================================

def search_by_article(article_number, source_type=None, limit=10):

    # Filter by article number
    conditions = [
        FieldCondition(
            key="article_number",
            match=MatchValue(value=article_number)
        )
    ]

    # Add source type filter if specified
    if source_type:
        conditions.append(
            FieldCondition(
                key="source_type",
                match=MatchValue(value=source_type)
            )
        )

    points, _ = client.scroll(
        collection_name=collection,
        scroll_filter=Filter(
            must=conditions
        ),
        limit=limit,
        with_payload=True,
        with_vectors=False
    )

    return points