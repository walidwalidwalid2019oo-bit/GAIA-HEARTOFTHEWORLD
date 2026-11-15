"""GAIA central orchestration: specialist selection, memory, and model call."""
from __future__ import annotations

from gaia.ai.memory import ConversationMemory
from gaia.ai.provider import OpenAICompatibleProvider, ProviderError
from gaia.ai.specialists import SPECIALISTS, choose_specialist


class GaiaAI:
    def __init__(self) -> None:
        self.provider = OpenAICompatibleProvider()
        self.memory = ConversationMemory()

    def status(self) -> dict[str, object]:
        return {
            "provider_configured": self.provider.ready(),
            "model": self.provider.model or None,
            "specialists": list(SPECIALISTS.keys()),
            "memory": "sqlite",
        }

    def respond(\n        self,\n        message: str,\n        conversation_id: str = "default",\n        specialist_name: str | None = None,\n    ) -> dict[str, str]:\n        specialist_name = specialist_name or choose_specialist(message)\n        if specialist_name not in SPECIALISTS:\n            raise ValueError("Unknown GAIA specialist.")\n        specialist = SPECIALISTS[specialist_name]
        history = self.memory.recent(conversation_id)
        system_prompt = (
            SPECIALISTS["GAIA"]["instruction"] + "\n\n"
            + "Current specialist perspective: " + specialist_name + " — " + specialist["role"] + ".\n"
            + specialist["instruction"] + "\n\n"
            + "Specialist focus: " + specialist["focus"] + "\n"
            + "You are one coordinated GAIA system. Do not claim separate autonomous agents are running; this version selects a specialist instruction within one model call."
        )
        messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": message}]
        answer = self.provider.chat(messages)
        self.memory.add(conversation_id, "user", message)
        self.memory.add(conversation_id, "assistant", answer)
        return {"answer": answer, "specialist": specialist_name, "conversation_id": conversation_id}
