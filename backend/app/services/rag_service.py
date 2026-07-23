"""
RAG Service — Retrieval-Augmented Generation over USCIS knowledge base.

Handles:
1. Embedding user queries
2. Retrieving relevant context from ChromaDB
3. Assembling prompts with context
4. Generating cited responses
"""

import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

from app.core.config import get_settings
from app.utils.citations import format_inline_citation

logger = logging.getLogger(__name__)


class RAGService:
    """Manages the vector store and retrieval pipeline."""

    def __init__(self):
        self.settings = get_settings()
        self.openai_client = OpenAI(api_key=self.settings.openai_api_key)
        self._init_chroma()

    def _init_chroma(self):
        """Initialize ChromaDB client and collection."""
        persist_dir = Path(self.settings.resolved_chroma_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Main collection for USCIS policy documents
        self.policy_collection = self.chroma_client.get_or_create_collection(
            name="uscis_policy",
            metadata={"description": "USCIS Policy Manual, Form Instructions, and Guidance"},
        )

        # Separate collection for processing times (updated frequently)
        self.timeline_collection = self.chroma_client.get_or_create_collection(
            name="processing_times",
            metadata={"description": "USCIS Processing Times Data"},
        )

        doc_count = self.policy_collection.count()
        logger.info(f"ChromaDB initialized. Policy documents: {doc_count}")

    # ----- Embedding -----

    def get_embedding(self, text: str) -> list[float]:
        """Generate embedding using OpenAI's text-embedding-3-small."""
        response = self.openai_client.embeddings.create(
            model=self.settings.embedding_model,
            input=text,
        )
        return response.data[0].embedding

    # ----- Document Ingestion -----

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict],
        ids: list[str],
        collection_name: str = "uscis_policy",
    ):
        """Add documents to the vector store in batches."""
        collection = (
            self.policy_collection
            if collection_name == "uscis_policy"
            else self.timeline_collection
        )

        # Generate embeddings
        embeddings = []
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            response = self.openai_client.embeddings.create(
                model=self.settings.embedding_model,
                input=batch,
            )
            embeddings.extend([e.embedding for e in response.data])
            logger.info(f"Embedded batch {i // batch_size + 1}")

        # Add to ChromaDB
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info(f"Added {len(documents)} documents to {collection_name}")

    # ----- Retrieval -----

    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        collection_name: str = "uscis_policy",
        where_filter: Optional[dict] = None,
    ) -> list[dict]:
        """
        Retrieve the most relevant documents for a query.

        Returns list of {document, metadata, distance} dicts.
        """
        collection = (
            self.policy_collection
            if collection_name == "uscis_policy"
            else self.timeline_collection
        )

        if collection.count() == 0:
            logger.warning(f"Collection {collection_name} is empty!")
            return []

        query_embedding = self.get_embedding(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        retrieved = []
        for i in range(len(results["documents"][0])):
            retrieved.append(
                {
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )

        logger.info(f"Retrieved {len(retrieved)} documents for query: {query[:80]}...")
        return retrieved

    def format_context(self, retrieved_docs: list[dict]) -> tuple[str, list[str]]:
        """
        Format retrieved documents into context string + source list.

        Returns:
            (context_string, list_of_source_names)
        """
        if not retrieved_docs:
            return "No relevant context found in the knowledge base.", []

        context_parts = []
        sources = []

        for i, doc in enumerate(retrieved_docs, 1):
            source_name = doc["metadata"].get("source", "USCIS Document")
            section = doc["metadata"].get("section", "")
            source_label = f"{source_name} — {section}" if section else source_name
            inline = format_inline_citation(source_label, i)

            context_parts.append(
                f"{inline}\n{doc['document']}\n"
            )
            sources.append(source_label)

        context = "\n---\n".join(context_parts)
        return context, sources


# Singleton
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create singleton RAG service."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
