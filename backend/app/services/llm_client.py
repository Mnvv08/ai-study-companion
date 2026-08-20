"""
app/services/llm_client.py
──────────────────────────
Wrapper for calling OpenAI LLM (gpt-4o-mini).
"""

import json
from openai import OpenAI
from typing import Dict, Any, List

from app.core.config import settings


class LLMClientService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL

    def generate_study_notes(self, text_content: str) -> Dict[str, Any]:
        """
        Generates structured, exam-ready study notes in JSON format.
        """
        system_prompt = (
            "You are a study assistant that converts raw study material into structured, exam-ready notes.\n"
            "Rules:\n"
            "- Use ONLY the provided content. Do not add outside facts.\n"
            "- Organize into clear sections with headings.\n"
            "- Use bullet points for details.\n"
            "- If the content includes definitions, list them under 'key_terms'.\n"
            "- Return valid JSON matching this schema exactly:\n"
            "{\n"
            '  "title": "string",\n'
            '  "sections": [{"heading": "string", "points": ["string"]}],\n'
            '  "key_terms": [{"term": "string", "definition": "string"}]\n'
            "}"
        )

        user_prompt = f"Study Material:\n\n{text_content[:15000]}"  # Truncate if exceptionally huge

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            raise RuntimeError(f"LLM study notes generation failed: {str(e)}")

    def answer_question_with_context(self, question: str, context_chunks: List[str]) -> str:
        """
        Answers a user question based strictly on retrieved context chunks (RAG).
        """
        context_str = "\n\n---\n\n".join(context_chunks)

        system_prompt = (
            "You are a study assistant helping a student understand their course material.\n"
            "Rules:\n"
            "- Answer ONLY using the information in the provided context chunks.\n"
            "- If the answer is not present in the context, say: 'I couldn't find this in your uploaded material.' Do not guess or use outside knowledge.\n"
            "- Keep answers clear, accurate, and exam-relevant."
        )

        user_prompt = f"Context:\n{context_str}\n\nQuestion: {question}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise RuntimeError(f"LLM Q&A generation failed: {str(e)}")
