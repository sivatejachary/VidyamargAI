"""
VidyaMarg AI — Job Discovery Domain Exceptions
===============================================
All domain-level errors are typed explicitly to allow
precise error handling at the application and API layers.
"""
from __future__ import annotations


class JobDiscoveryError(Exception):
    """Base error for all job discovery domain failures."""
    pass


# ---------------------------------------------------------------------------
# Connector Errors
# ---------------------------------------------------------------------------

class ConnectorError(JobDiscoveryError):
    """Raised when a connector encounters an unrecoverable error."""
    def __init__(self, connector_name: str, message: str) -> None:
        self.connector_name = connector_name
        super().__init__(f"[{connector_name}] {message}")


class ConnectorAuthError(ConnectorError):
    """Raised when a connector fails to authenticate."""
    pass


class ConnectorRateLimitError(ConnectorError):
    """Raised when a connector hits a rate limit (HTTP 429)."""
    pass


class ConnectorTimeoutError(ConnectorError):
    """Raised when a connector request times out."""
    pass


class ConnectorCircuitOpenError(ConnectorError):
    """Raised when the circuit breaker for a connector is open."""
    pass


class ConnectorNotFoundError(JobDiscoveryError):
    """Raised when requesting a connector that does not exist in the registry."""
    def __init__(self, name: str) -> None:
        super().__init__(f"Connector '{name}' is not registered in the connector registry.")


# ---------------------------------------------------------------------------
# Pipeline Errors
# ---------------------------------------------------------------------------

class NormalizationError(JobDiscoveryError):
    """Raised when a job cannot be normalized due to missing required fields."""
    pass


class ValidationError(JobDiscoveryError):
    """Raised when a job fails validation rules."""
    def __init__(self, message: str, errors: list | None = None) -> None:
        self.errors = errors or []
        super().__init__(message)


class DeduplicationError(JobDiscoveryError):
    """Raised when deduplication logic encounters an unexpected failure."""
    pass


class EnrichmentError(JobDiscoveryError):
    """Raised when AI enrichment fails for a job."""
    pass


# ---------------------------------------------------------------------------
# Persistence Errors
# ---------------------------------------------------------------------------

class PersistenceError(JobDiscoveryError):
    """Raised when a bulk persistence operation fails."""
    pass


class RepositoryError(JobDiscoveryError):
    """Raised for repository-level DB errors."""
    pass


class DuplicateJobError(JobDiscoveryError):
    """Raised when a job is found to be a duplicate of an existing record."""
    def __init__(self, external_id: str, existing_id: int) -> None:
        self.external_id = external_id
        self.existing_id = existing_id
        super().__init__(f"Job '{external_id}' is a duplicate of DB record #{existing_id}")


# ---------------------------------------------------------------------------
# Embedding & Vector Errors
# ---------------------------------------------------------------------------

class EmbeddingError(JobDiscoveryError):
    """Raised when embedding generation fails."""
    pass


class QdrantError(JobDiscoveryError):
    """Raised when Qdrant operations fail."""
    pass


class QdrantUnavailableError(QdrantError):
    """Raised when Qdrant is offline — triggers DB fallback."""
    pass


# ---------------------------------------------------------------------------
# Matching & Recommendation Errors
# ---------------------------------------------------------------------------

class MatchingError(JobDiscoveryError):
    """Raised when the matching engine encounters an unrecoverable error."""
    pass


class RecommendationError(JobDiscoveryError):
    """Raised when recommendation generation fails."""
    pass


# ---------------------------------------------------------------------------
# Buffer Errors
# ---------------------------------------------------------------------------

class BufferError(JobDiscoveryError):
    """Raised when the Redis collector buffer operation fails."""
    pass


class BufferUnavailableError(BufferError):
    """Raised when Redis is unavailable — triggers local in-memory fallback."""
    pass
