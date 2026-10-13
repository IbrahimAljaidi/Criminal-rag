from splitter import load_and_split
from emb import create_embeddings
from qdrant import save_chunks


def index_data():

    # Load and split the legal document
    chunks = load_and_split()

    print(f"Total chunks: {len(chunks)}")

    # Create Gemini embeddings for all chunks
    print("Creating embeddings...")

    vectors = create_embeddings(chunks)

    print(f"Total vectors: {len(vectors)}")

    # Make sure every chunk has a vector
    if len(chunks) != len(vectors):
        raise ValueError(
            "The number of chunks does not match the number of vectors."
        )

    # Save chunks and vectors to Qdrant
    print("Saving data to Qdrant...")

    save_chunks(chunks, vectors)

    print("Data saved successfully.")


if __name__ == "__main__":
    index_data()