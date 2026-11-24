# uni-rag-retrieval

Routes queries, searches the indexed stores, reranks candidates, and composes answers.

Owned by the **retrieval lane**; depends only on `uni-rag-core` contracts. Indexing
is reached through core ports, never through a package-to-package import.
