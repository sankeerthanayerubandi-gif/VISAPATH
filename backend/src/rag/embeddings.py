"""Thin wrapper so the embedding model is configured in exactly one place."""
from langchain_openai import OpenAIEmbeddings
from backend.config.settings import EMBEDDING_MODEL, OPENAI_API_KEY


def get_embeddings():
    return OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
