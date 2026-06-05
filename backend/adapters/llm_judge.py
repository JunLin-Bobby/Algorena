"""LLM-based judge adapter using OpenAI SDK."""

import json
from typing import Any

from openai import AsyncOpenAI

from core.ports import IJudgeService, JudgeResult


class LLMJudgeService(IJudgeService):
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        base_url: str | None = None,
        timeout_seconds: float = 20.0,
        max_tokens: int = 1024,
        client: Any | None = None,
    ) -> None:
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_tokens = max_tokens
        if client is not None:
            self._client = client
            return
        if not api_key:
            raise ValueError("api_key is required when no custom client is provided")
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )

    async def judge(self, question: str, code: str) -> JudgeResult:
        try:
            prompt = self._build_user_prompt(question, code)
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=self._max_tokens,
            )
        except Exception:
            return self._fallback_result("judge provider unavailable")

        raw_text = str(response.choices[0].message.content or "").strip()
        return self._parse_result(raw_text)

    def _parse_result(self, raw_text: str) -> JudgeResult:
        cleaned = self._strip_markdown_json_block(raw_text)
        try:
            payload = json.loads(cleaned)
        except Exception:
            return self._fallback_result("failed to parse judge result")

        if not isinstance(payload, dict):
            return self._fallback_result("failed to parse judge result")

        score = self._normalize_score(payload.get("score"))
        feedback = str(payload.get("feedback", "")).strip()
        if not feedback:
            feedback = "No feedback returned by judge."
        return {"score": score, "feedback": feedback}

    def _normalize_score(self, value: Any) -> float:
        try:
            score = float(value)
        except Exception:
            score = 0.0
        return max(0.0, min(10.0, score))

    def _fallback_result(self, reason: str) -> JudgeResult:
        return {"score": 0.0, "feedback": f"{reason}; default score applied."}

    def _strip_markdown_json_block(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned.startswith("```"):
            return cleaned
        lines = cleaned.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
        return cleaned

    def _system_prompt(self) -> str:
        return (
            "You are the host of a competitive programming quiz show — sharp, warm, "
            "and a little theatrical. You celebrate good ideas, gently roast mistakes, "
            "and keep feedback fun without being mean or unprofessional.\n\n"
            "Evaluate the submitted code and return ONLY a JSON object. "
            "No explanation outside JSON, no markdown, no code block.\n\n"
            "JSON schema:\n"
            "{\n"
            '  "score": <number 0.0-10.0>,\n'
            '  "feedback": <string, 2-3 sentences max>\n'
            "}\n\n"
            "Feedback style:\n"
            "- Sound like a quiz show host: energetic, witty, human, encouraging.\n"
            "- Mention what worked or what missed the mark in plain language.\n"
            "- Stay concise; no bullet lists inside feedback.\n\n"
            "Example output:\n"
            '{"score": 7.2, "feedback": "Nice sliding-window instinct — you almost had '
            "the audience on their feet! Time complexity is solid, but a clearer variable "
            'name would help the judges at home follow along."}'
        )

    def _build_user_prompt(self, question: str, code: str) -> str:
        return (
            "## Question\n"
            f"{question}\n\n"
            "## Submitted Code\n"
            f"```\n{code}\n```\n\n"
            "Score the submission like a quiz show round. Consider:\n"
            "- Correctness: does it solve the problem? (5 pts)\n"
            "- Time complexity: is the algorithm efficient? (3 pts)\n"
            "- Code quality: readability, naming, structure (2 pts)\n\n"
            "Write feedback in a lively, host-like voice — fun and human, not robotic.\n"
            "Return ONLY the JSON object."
        )
