import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct


load_dotenv()


# بيانات الاتصال بـ Qdrant
qdrant_url = os.getenv("QDRANT_URL")
qdrant_api = os.getenv("QDRANT_API_KEY")
collection = os.getenv("QDRANT_COLLECTION")


# الاتصال بـ Qdrant
client = QdrantClient(
    url=qdrant_url,
    api_key=qdrant_api
)


# ==========================================
# تخزين الـ Chunks والـ Vectors
# ==========================================

def save_chunks(chunks, vectors):

    # قائمة لتجميع الـ Points
    points = []

    # ربط كل Chunk بالـ Vector الخاص به
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):

        point = PointStruct(
            id=i,

            # الـ Vector الخاص بالـ Chunk
            vector=vector,

            # البيانات المرتبطة بالـ Vector
            payload={
                "chunk_id": i,
                "text": chunk
            }
        )

        points.append(point)

    # تخزين جميع الـ Points في Qdrant
    client.upsert(
        collection_name=collection,
        points=points
    )


# ==========================================
# البحث عن أقرب Chunks
# ==========================================

def search_chunks(query_vector, limit=5):

    result = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=limit
    )

    return result.points