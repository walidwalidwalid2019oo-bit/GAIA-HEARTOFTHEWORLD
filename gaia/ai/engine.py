"""GAIA central orchestration: specialist selection, memory, and model call."""
from __future__ import annotations

from gaia.ai.memory import ConversationMemory
from gaia.storage import database_backend
from gaia.ai.provider import OpenAICompatibleProvider
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
            "memory": "database_backed",
            "database_backend": database_backend(self.memory.engine),
        }

    def respond(
        self,
        message: str,
        conversation_id: str = "default",
        specialist_name: str | None = None,
    ) -> dict[str, str]:
        selected_specialist = specialist_name or choose_specialist(message)
        if selected_specialist not in SPECIALISTS:
            raise ValueError("Unknown GAIA specialist.")

        specialist = SPECIALISTS[selected_specialist]
        history = self.memory.recent(conversation_id)
        system_prompt = (
            SPECIALISTS["GAIA"]["instruction"] + "\n\n"
            + "Current specialist perspective: " + selected_specialist + " — " + specialist["role"] + ".\n"
            + specialist["instruction"] + "\n\n"
            + "Specialist focus: " + specialist["focus"] + "\n"
            + "You are one coordinated GAIA system. Do not claim separate autonomous agents are running; "
            "this version selects a specialist instruction within one model call."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": message},
        ]
        answer = self.provider.chat(messages)
        self.memory.add(conversation_id, "user", message)
        self.memory.add(conversation_id, "assistant", answer)
        return {
            "answer": answer,
            "specialist": selected_specialist,
            "conversation_id": conversation_id,
        }
