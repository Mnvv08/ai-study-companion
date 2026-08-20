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
        """Generates structured, exam-ready study notes in JSON format."""
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

        user_prompt = f"Study Material:\n\n{text_content[:15000]}"

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
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            raise RuntimeError(f"LLM study notes generation failed: {str(e)}")

    def generate_flashcards(self, text_content: str, count: int = 10) -> List[Dict[str, str]]:
        """Generates active-recall flashcards (Front/Back) from study content."""
        system_prompt = (
            "You are an expert tutor creating study flashcards for active recall.\n"
            "Rules:\n"
            "- Base flashcards strictly on the provided study material.\n"
            "- 'front' should be a concise question or concept.\n"
            "- 'back' should be a clear, accurate answer or explanation.\n"
            "- Return JSON in this exact structure:\n"
            '{"flashcards": [{"front": "string", "back": "string"}]}'
        )

        user_prompt = f"Generate exactly {count} flashcards from this text:\n\n{text_content[:15000]}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("flashcards", [])
        except Exception as e:
            raise RuntimeError(f"LLM flashcards generation failed: {str(e)}")

    def generate_mcqs(self, text_content: str, count: int = 5) -> List[Dict[str, Any]]:
        """Generates multiple choice questions with 4 options and explanations."""
        system_prompt = (
            "You are a professor creating exam-grade Multiple Choice Questions (MCQs).\n"
            "Rules:\n"
            "- Questions must be derived strictly from the text.\n"
            "- Provide exactly 4 options per question.\n"
            "- 'correct_answer' MUST be identical to one of the strings in 'options'.\n"
            "- 'explanation' should explain why that answer is correct based on the text.\n"
            "- Return JSON in this exact structure:\n"
            '{"mcqs": [{"id": 1, "question": "string", "options": ["A", "B", "C", "D"], "correct_answer": "string", "explanation": "string"}]}'
        )

        user_prompt = f"Generate exactly {count} MCQs from this text:\n\n{text_content[:15000]}"

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
            result = json.loads(response.choices[0].message.content)
            return result.get("mcqs", [])
        except Exception as e:
            raise RuntimeError(f"LLM MCQ generation failed: {str(e)}")

    def generate_short_questions(self, text_content: str, count: int = 5) -> List[Dict[str, Any]]:
        """Generates conceptual short-answer questions with key evaluation points."""
        system_prompt = (
            "You are an examiner writing short-answer university exam questions.\n"
            "Rules:\n"
            "- Formulate analytical/conceptual questions grounded in the text.\n"
            "- 'sample_answer' should be a model student response (2-4 sentences).\n"
            "- 'key_points' should be bullet points required for full credit.\n"
            "- Return JSON in this exact structure:\n"
            '{"questions": [{"id": 1, "question": "string", "sample_answer": "string", "key_points": ["string"]}]}'
        )

        user_prompt = f"Generate exactly {count} short-answer questions from this text:\n\n{text_content[:15000]}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("questions", [])
        except Exception as e:
            raise RuntimeError(f"LLM short questions generation failed: {str(e)}")

    def answer_question_with_context(self, question: str, context_chunks: List[str]) -> str:
        """Answers a user question based strictly on retrieved context chunks (RAG)."""
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
