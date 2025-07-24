"""Minimal shim so that SpecialistAgent can instantiate a code-aware LLM agent.

The original FriendlyCodeAgent used by smolagents isn't in this repository.
For now we expose the subset of behaviour SpecialistAgent relies on:

* __init__(tools, model, max_steps)
* run(prompt) -> str

All other parameters are accepted but ignored.  The *model* argument must have
either a ``run`` method or be directly callable (``model(prompt)``).
"""

from __future__ import annotations

from typing import Any, Callable, List


class FriendlyCodeAgent:  # noqa: D101 – minimal stub
    def __init__(self, tools: List[Callable] | None = None, model: Any | None = None, max_steps: int = 1):
        self.tools = tools or []
        self.model = model
        self.max_steps = max_steps

    # ------------------------------------------------------------------
    # Public API expected by SpecialistAgent
    # ------------------------------------------------------------------
    def run(self, prompt: str, *args, **kwargs):  # noqa: D401 – external contract
        """Return the model's response to *prompt*.

        If the supplied *model* has a ``run`` method we call it, otherwise we
        assume it's directly callable.
        """
        if self.model is None:
            raise RuntimeError("FriendlyCodeAgent was created without a model.")

        try:
            if callable(getattr(self.model, "run", None)):
                return self.model.run(prompt, *args, **kwargs)
            if callable(self.model):
                return self.model(prompt, *args, **kwargs)
            raise TypeError("Model provided to FriendlyCodeAgent is not callable.")
        except Exception as exc:  # noqa: BLE001 – propagate as string
            # Return a plain-text error so caller can gracefully degrade.
            return f"ModelError: {exc}" 