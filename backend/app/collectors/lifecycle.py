"""Collector Lifecycle Documentation.

This module documents the lifecycle of a job collection run.
It contains no executable logic — only annotations and documentation
constants that describe the expected flow.
"""

from enum import Enum


class CollectorStage(str, Enum):
    """Enumeration of all stages in the collector lifecycle.

    Each stage corresponds to a method on BaseCollector.
    """

    INITIALIZE = "initialize"
    """Set up resources (browser, session, API client)."""

    COLLECT = "collect"
    """Execute the search and gather raw data from the source."""

    NORMALIZE = "normalize"
    """Convert raw source data into normalized JobData models."""

    VALIDATE = "validate"
    """Validate normalized data and remove invalid entries."""

    DEDUPLICATE = "deduplicate"
    """Remove jobs already present in the database."""

    SAVE = "save"
    """Persist validated, de-duplicated jobs to storage."""

    CLEANUP = "cleanup"
    """Release resources. Always called, even on failure."""


LIFECYCLE_ORDER: list[CollectorStage] = [
    CollectorStage.INITIALIZE,
    CollectorStage.COLLECT,
    CollectorStage.NORMALIZE,
    CollectorStage.VALIDATE,
    CollectorStage.DEDUPLICATE,
    CollectorStage.SAVE,
    CollectorStage.CLEANUP,
]
"""The canonical order of lifecycle stages.

The execute() method on BaseCollector follows this exact order.
CLEANUP is guaranteed to run in a finally block.
"""


class CollectorState(str, Enum):
    """Possible states for a collector instance."""

    CREATED = "created"
    """Collector instance created but not yet initialized."""

    INITIALIZED = "initialized"
    """Collector resources are ready."""

    COLLECTING = "collecting"
    """Actively collecting data from the source."""

    PROCESSING = "processing"
    """Normalizing, validating, and deduplicating collected data."""

    SAVING = "saving"
    """Persisting processed jobs."""

    COMPLETED = "completed"
    """Collection run finished successfully."""

    FAILED = "failed"
    """Collection run terminated with an error."""

    CLEANED_UP = "cleaned_up"
    """Resources have been released."""


# Lifecycle guarantees:
# 1. initialize() is always called before collect()
# 2. cleanup() is always called after the run, even on failure
# 3. normalize() receives the raw output of collect()
# 4. validate() receives the output of normalize()
# 5. deduplicate() receives the output of validate()
# 6. save() is the final processing step before cleanup
