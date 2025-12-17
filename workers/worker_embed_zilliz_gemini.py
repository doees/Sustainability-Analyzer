import os
import json
import uuid
from dotenv import load_dotenv

import google.generativeai as genai
from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility
)


# Load Environment Variables

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004")

ZILLIZ_URI = os.getenv("ZILLIZ_URI")
ZILLIZ_TOKEN = os.getenv("ZILLIZ_TOKEN")
ZILLIZ_DB = os.getenv("ZILLIZ_DB", "default")
ZILLIZ_COLLECTION = os.getenv("ZILLIZ_COLLECTION_SR", "sr_chunks")

BASE_DATA_DIR = "data/processed"


# Initialize Gemini

genai.configure(api_key=GEMINI_API_KEY)



# Zilliz / Milvus Setup

def connect_zilliz():
    connections.connect(
        alias="default",
        uri=ZILLIZ_URI,
        token=ZILLIZ_TOKEN,
        db_name=ZILLIZ_DB
    )


def create_collection_if_not_exists(dim: int):
    if utility.has_collection(ZILLIZ_COLLECTION):
        return

    fields = [
        FieldSchema(
            name="id",
            dtype=DataType.VARCHAR,
            is_primary=True,
            max_length=64
        ),
        FieldSchema(
            name="embedding",
            dtype=DataType.FLOAT_VECTOR,
            dim=dim
        ),
        FieldSchema(
            name="text",
            dtype=DataType.VARCHAR,
            max_length=8192
        ),
        FieldSchema(
            name="job_id",
            dtype=DataType.VARCHAR,
            max_length=64
        ),
        FieldSchema(
            name="page",
            dtype=DataType.INT64
        )
    ]

    schema = CollectionSchema(fields, description="Sustainability Report Chunks")
    collection = Collection(name=ZILLIZ_COLLECTION, schema=schema)

    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128}
    }

    collection.create_index(
        field_name="embedding",
        index_params=index_params
    )

    collection.load()



# Embedding Function (Gemini)

def get_embedding(text: str) -> list:
    """
    Generate embedding vector using Gemini Embedding API
    """
    response = genai.embed_content(
        model=GEMINI_EMBED_MODEL,
        content=text
    )
    return response["embedding"]



# Load Chunks

def load_chunks(job_id: str) -> list:
    chunk_path = os.path.join(BASE_DATA_DIR, job_id, "chunks.json")

    if not os.path.exists(chunk_path):
        raise FileNotFoundError(f"Chunks file not found: {chunk_path}")

    with open(chunk_path, "r", encoding="utf-8") as f:
        return json.load(f)



# Store Embeddings to Zilliz

def store_embeddings(job_id: str, chunks: list):
    embeddings = []
    texts = []
    ids = []
    pages = []

    for chunk in chunks:
        emb = get_embedding(chunk["text"])

        embeddings.append(emb)
        texts.append(chunk["text"])
        ids.append(str(uuid.uuid4()))
        pages.append(chunk.get("page", -1))

    collection = Collection(ZILLIZ_COLLECTION)

    collection.insert([
        ids,
        embeddings,
        texts,
        [job_id] * len(ids),
        pages
    ])

    collection.flush()



# Main Worker Function

def main(job_id: str):
    print(f"[INFO] Start embedding job: {job_id}")

    connect_zilliz()

    chunks = load_chunks(job_id)

    # Create collection lazily based on embedding dimension
    sample_embedding = get_embedding(chunks[0]["text"])
    create_collection_if_not_exists(dim=len(sample_embedding))

    store_embeddings(job_id, chunks)

    print(f"[SUCCESS] Embedding job completed: {job_id}")



# CLI Support

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python worker_embed_zilliz_gemini.py <job_id>")
        sys.exit(1)

    main(sys.argv[1])
