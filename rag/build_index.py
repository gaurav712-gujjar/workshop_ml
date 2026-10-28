<<<<<<< HEAD
"""Build the RAG vector store (chunks -> TF-IDF -> FAISS).

Run from the project root whenever the knowledge base changes:

    python -m rag.build_index
"""
=======
>>>>>>> 80733a1 (voice assisent  Completed)
import sys

from src.exception import CustomException
from src.logger import get_logger
from rag.document_loader import build_chunks
from rag.rag_config_loader import load_rag_config
from rag.vector_store import VectorStore

logger = get_logger(__name__)


def main():
    try:
        config = load_rag_config()
        kb = config["knowledge_base"]
<<<<<<< HEAD

        chunks = build_chunks(
            kb["source_dir"], kb["chunk_size"], kb["chunk_overlap"]
        )
        if not chunks:
            raise RuntimeError(f"No .md documents found in {kb['source_dir']}")

=======
        chunks = build_chunks(kb["source_dir"], kb["chunk_size"], kb["chunk_overlap"])
        if not chunks:
            raise RuntimeError(f"No .md documents found in {kb['source_dir']}")
>>>>>>> 80733a1 (voice assisent  Completed)
        VectorStore(config).build(chunks)
        print(f"Index built from {len(chunks)} chunks.")
    except Exception as e:
        raise CustomException(e, sys) from e


if __name__ == "__main__":
<<<<<<< HEAD
    main()
=======
    main()
>>>>>>> 80733a1 (voice assisent  Completed)
