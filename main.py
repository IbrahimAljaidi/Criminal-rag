# استيراد دالة تقسيم النص إلى Chunks
from documents.splitter import load_and_split

# استيراد دالة تحويل الـ Chunks إلى Embeddings
from embeddings.emb import create_embeddings

# استيراد دالة تخزين البيانات في Qdrant
from database.qdrant import save_chunks

