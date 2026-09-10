from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

client = OpenAI()


def create_embedding(text):

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )

    return response.data[0].embedding


def create_embeddings(chunks):

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=chunks
    )

    vectors = [
        item.embedding
        for item in response.data
    ]

    return vectors