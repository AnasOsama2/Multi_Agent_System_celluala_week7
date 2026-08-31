"""
Shared abstractions: Tool and Agent base classes.

Every concrete tool plugs into an agent the same way (Strategy pattern),
and every agent exposes the same run() contract, so an Orchestrator
(outside the scope of this task) can treat Retriever / Analyst / Answer
agents interchangeably.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any


class ToolExecutionError(RuntimeError):
    """Raised when a tool fails to complete its job."""


class Tool(ABC):
    """Base class for every tool an agent can call."""

    name: str
    description: str

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute the tool and return its result."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Tool {self.name}>"


class Agent(ABC):
    """
    Base class for the three specialised agents. Holds a registry of the
    tools it owns and a logger; concrete agents implement `run`.
    """

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {t.name: t for t in (tools or [])}
        self._logger = logging.getLogger(self.__class__.__name__)

    def register_tool(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def use_tool(self, name: str, **kwargs: Any) -> Any:
        if name not in self._tools:
            raise ToolExecutionError(f"Tool '{name}' is not registered on {self}")
        self._logger.debug("Calling tool %s with %s", name, kwargs)
        try:
            return self._tools[name].run(**kwargs)
        except ToolExecutionError:
            raise
        except Exception as exc:  # re-raise as a domain-specific error
            raise ToolExecutionError(f"Tool '{name}' failed: {exc}") from exc

    @property
    def tools(self) -> list[str]:
        return list(self._tools.keys())

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} tools={self.tools}>"
