from langchain_huggingface import HuggingFaceEmbeddings
from config import settings

embedding_model = HuggingFaceEmbeddings(
    model_name=settings.llm.embedding_model,
)


def get_embedding_model():
    return embedding_model
