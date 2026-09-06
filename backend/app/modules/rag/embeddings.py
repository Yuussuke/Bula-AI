from langchain_core.embeddings import Embeddings as LCEmbeddings


E5_INPUT_CONTRACT = "e5-query-passage-v1"
PLAIN_INPUT_CONTRACT = "plain-v1"


class EmbeddingAdapter:
    def __init__(
        self,
        embedder: LCEmbeddings,
        batch_size: int = 32,
        dimension: int = 1024,
        validate_dimension: bool = True,
        model_name: str = "unspecified",
    ) -> None:
        if batch_size <= 0:
            raise ValueError("Embedding batch_size must be greater than zero.")

        if dimension <= 0:
            raise ValueError("Embedding dimension must be greater than zero.")

        self._embedder = embedder
        self._batch_size = batch_size
        self._dimension = dimension
        self._validate_dimension = validate_dimension
        self._model_name = model_name.strip() or "unspecified"
        self._uses_e5_input_contract = self._is_e5_model(self._model_name)

    @property
    def embedding_profile(self) -> str:
        input_contract = (
            E5_INPUT_CONTRACT if self._uses_e5_input_contract else PLAIN_INPUT_CONTRACT
        )
        return f"{self._model_name};input={input_contract}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []

        for batch_start in range(0, len(texts), self._batch_size):
            batch_end = batch_start + self._batch_size
            text_batch = [
                self._prepare_document_text(text)
                for text in texts[batch_start:batch_end]
            ]
            batch_vectors = self._embedder.embed_documents(text_batch)
            vectors.extend(batch_vectors)

        if len(vectors) != len(texts):
            raise ValueError(
                "Embedding provider returned "
                f"{len(vectors)} vectors for {len(texts)} input texts."
            )

        self._validate_vectors(vectors)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        prepared_text = self._prepare_query_text(text)
        vector = self._embedder.embed_query(prepared_text)
        self._validate_vector(vector=vector, vector_label="query")
        return vector

    def _validate_vectors(self, vectors: list[list[float]]) -> None:
        for vector_index, vector in enumerate(vectors):
            self._validate_vector(
                vector=vector,
                vector_label=f"document at index {vector_index}",
            )

    def _validate_vector(self, *, vector: list[float], vector_label: str) -> None:
        if not self._validate_dimension:
            return

        vector_dimension = len(vector)
        if vector_dimension == self._dimension:
            return

        raise ValueError(
            f"Embedding vector for {vector_label} has {vector_dimension} dimensions; "
            f"expected {self._dimension}."
        )

    def _prepare_document_text(self, text: str) -> str:
        if not self._uses_e5_input_contract:
            return text

        return self._ensure_prefix(text=text, prefix="passage: ")

    def _prepare_query_text(self, text: str) -> str:
        if not self._uses_e5_input_contract:
            return text

        return self._ensure_prefix(text=text, prefix="query: ")

    def _ensure_prefix(self, *, text: str, prefix: str) -> str:
        if text.lstrip().lower().startswith(prefix):
            return text

        return f"{prefix}{text}"

    def _is_e5_model(self, model_name: str) -> bool:
        normalized_model_name = model_name.lower().replace("_", "-")
        return (
            "e5-" in normalized_model_name or "multilingual-e5" in normalized_model_name
        )
