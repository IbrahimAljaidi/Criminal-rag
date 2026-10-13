import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def create_embedding(text):

    # Create an embedding for the user's search query
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768
        )
    )

    return response.embeddings[0].values

def create_embeddings(chunks):

    # Extract only the text from each chunk
    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    vectors = []

    batch_size = 100

    for i in range(0, len(texts), batch_size):

        batch = texts[i:i + batch_size]

        print(
            f"Embedding batch "
            f"{i + 1}-{min(i + batch_size, len(texts))} "
            f"of {len(texts)}"
        )

        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=batch,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=768
            )
        )

        batch_vectors = [
            embedding.values
            for embedding in response.embeddings
        ]

        vectors.extend(batch_vectors)

        # Wait before sending the next batch
        if i + batch_size < len(texts):
            print("Waiting 65 seconds...")
            time.sleep(65)

    return vectors
