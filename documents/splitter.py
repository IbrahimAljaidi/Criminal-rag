TEXT_PATH = "data/criminal_procedure.txt"

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start = end - overlap

    return chunks


def load_and_split():

    with open(TEXT_PATH, "r", encoding="utf-8") as file:
        text = file.read()

    chunks = split_text(text)

    return chunks