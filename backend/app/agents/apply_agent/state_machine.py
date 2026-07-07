from __future__ import annotations

from enum import Enum, auto
from typing import Optional

from app.agents.apply_agent.exceptions import StateTransitionError


class ApplicationState(str, Enum):
    INITIALIZED = "initialized"
    PAGE_LOADED = "page_loaded"
    ANALYZED = "analyzed"
    FILLED = "filled"
    UPLOADED = "uploaded"
    REVIEWED = "reviewed"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    FAILED = "failed"
    CANCELLED = "cancelled"


VALID_TRANSITIONS: dict[ApplicationState, set[ApplicationState]] = {
    ApplicationState.INITIALIZED: {ApplicationState.PAGE_LOADED, ApplicationState.FAILED, ApplicationState.CANCELLED},
    ApplicationState.PAGE_LOADED: {ApplicationState.ANALYZED, ApplicationState.FAILED, ApplicationState.CANCELLED},
    ApplicationState.ANALYZED: {ApplicationState.FILLED, ApplicationState.FAILED, ApplicationState.CANCELLED},
    ApplicationState.FILLED: {ApplicationState.UPLOADED, ApplicationState.REVIEWED, ApplicationState.FAILED, ApplicationState.CANCELLED},
    ApplicationState.UPLOADED: {ApplicationState.REVIEWED, ApplicationState.FAILED, ApplicationState.CANCELLED},
    ApplicationState.REVIEWED: {ApplicationState.SUBMITTED, ApplicationState.FAILED, ApplicationState.CANCELLED},
    ApplicationState.SUBMITTED: {ApplicationState.VERIFIED, ApplicationState.FAILED, ApplicationState.CANCELLED},
    ApplicationState.VERIFIED: set(),
    ApplicationState.FAILED: {ApplicationState.INITIALIZED, ApplicationState.CANCELLED},
    ApplicationState.CANCELLED: set(),
}


class StateMachine:
    """Tracks and validates application state transitions.

    Usage::

        sm = StateMachine()
        assert sm.state == ApplicationState.INITIALIZED
        sm.transition_to(ApplicationState.PAGE_LOADED)
        assert sm.state == ApplicationState.PAGE_LOADED
    """

    def __init__(self, initial_state: ApplicationState = ApplicationState.INITIALIZED) -> None:
        self._state = initial_state
        self._history: list[tuple[ApplicationState, ApplicationState, Optional[str]]] = []

    @property
    def state(self) -> ApplicationState:
        return self._state

    @property
    def history(self) -> list[tuple[ApplicationState, ApplicationState, Optional[str]]]:
        return list(self._history)

    def transition_to(self, target: ApplicationState, reason: Optional[str] = None) -> None:
        """Transition to a new state, validating the move.

        Args:
            target: The target state.
            reason: Optional reason for the transition.

        Raises:
            StateTransitionError: If the transition is not allowed.
        """
        if target not in VALID_TRANSITIONS.get(self._state, set()):
            raise StateTransitionError(
                message=f"Cannot transition from {self._state.value} to {target.value}",
                current_state=self._state.value,
                target_state=target.value,
            )
        previous = self._state
        self._state = target
        self._history.append((previous, target, reason))

    def can_transition_to(self, target: ApplicationState) -> bool:
        """Check whether a transition is allowed without performing it."""
        return target in VALID_TRANSITIONS.get(self._state, set())

    def reset(self, reason: Optional[str] = None) -> None:
        """Reset to initialized state (allows retry after failure)."""
        self.transition_to(ApplicationState.INITIALIZED, reason)
