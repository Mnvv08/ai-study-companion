import re
import json
import logging
from openai import OpenAI
from typing import Dict, Any, List

from app.core.config import settings

logger = logging.getLogger(__name__)


def extract_and_parse_json(content: str) -> Dict[str, Any]:
    """
    Defensively parses JSON from LLM output.
    Strips markdown code blocks, extracts {...} boundaries, and parses cleanly.
    """
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as err:
                raise ValueError(f"Extracted JSON block is malformed: {err}")
        raise ValueError(f"No valid JSON object found in response: {cleaned[:100]}")


class LLMClientService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL

    def generate_study_notes(self, text_content: str) -> Dict[str, Any]:
        """Generates structured, exam-ready study notes in JSON format."""
        system_prompt = (
            "You are a study assistant that converts raw study material into structured,\n"
            "exam-ready notes.\n"
            "Rules:\n"
            "- Use ONLY the provided content. Do not add outside facts.\n"
            "- Organize into clear sections with headings.\n"
            "- Use bullet points for details, not long paragraphs.\n"
            "- Bold key terms.\n"
            "- If the content includes definitions, list them separately under 'Key Terms'.\n"
            "- Return the output in the following JSON structure exactly:\n"
            '{ "title": "string", "sections": [{"heading": "string", "points": ["string"]}],\n'
            '  "key_terms": [{"term": "string", "definition": "string"}] }'
        )

        user_prompt = f'Study Material:\n"""\n{text_content[:20000]}\n"""'

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
            raw_text = response.choices[0].message.content or "{}"
            data = extract_and_parse_json(raw_text)

            if not isinstance(data, dict):
                raise ValueError("Parsed JSON root is not an object.")

            return {
                "title": str(data.get("title", "Study Notes")),
                "sections": list(data.get("sections", [])),
                "key_terms": list(data.get("key_terms", [])),
            }
        except Exception as e:
            logger.error(f"Study notes generation failed: {e}")
            raise RuntimeError(f"LLM study notes generation failed: {str(e)}")

    def generate_flashcards(self, text_content: str) -> List[Dict[str, Any]]:
        """Generates active-recall flashcards from study material with topic classification."""
        system_prompt = (
            "You are a study assistant that creates flashcards from study material.\n"
            "Rules:\n"
            "- Use ONLY the provided content. Do not add outside facts.\n"
            "- Each flashcard should test ONE clear concept — a term, a definition, a fact, or\n"
            "  a cause/effect relationship.\n"
            "- The 'front' should be a concise question or prompt. The 'back' should be a\n"
            "  concise, correct answer.\n"
            "- Decide the number of flashcards based on how much distinct, testable content is\n"
            "  in the material — do not pad with trivial or repetitive cards, and do not skip\n"
            "  genuinely important concepts to hit an arbitrary count.\n"
            "- Return the output in the following JSON structure exactly:\n"
            '{ "flashcards": [{"front": "string", "back": "string", "topic": "string"}] }'
        )

        user_prompt = f'Study Material:\n"""\n{text_content[:20000]}\n"""'

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
            raw_text = response.choices[0].message.content or "{}"
            data = extract_and_parse_json(raw_text)

            if not isinstance(data, dict):
                raise ValueError("Parsed JSON root is not an object.")

            flashcards = data.get("flashcards", [])
            cleaned_cards = []
            for item in flashcards:
                if isinstance(item, dict) and "front" in item and "back" in item:
                    cleaned_cards.append({
                        "front": str(item.get("front", "")).strip(),
                        "back": str(item.get("back", "")).strip(),
                        "topic": str(item.get("topic", "General")).strip() or "General",
                    })

            return cleaned_cards
        except Exception as e:
            logger.error(f"Flashcard generation failed: {e}")
            raise RuntimeError(f"LLM flashcard generation failed: {str(e)}")

    def generate_mcqs(self, text_content: str) -> List[Dict[str, Any]]:
        """Generates Multiple Choice Questions with 4 options, correct_index, and topic tags."""
        system_prompt = (
            "You are a study assistant that creates multiple-choice questions from study material.\n"
            "Rules:\n"
            "- Use ONLY the provided content. Do not add outside facts.\n"
            "- Each question must have exactly 4 options, with exactly ONE correct answer.\n"
            "- Incorrect options (distractors) should be plausible, not obviously wrong — they\n"
            "  should reflect common misconceptions or closely related but incorrect facts.\n"
            "- Decide the number of questions based on how much distinct, testable content exists\n"
            "  in the material — do not pad or skip content to hit an arbitrary count.\n"
            "- Tag each question with a short topic label representing the concept it tests.\n"
            "- Return the output in the following JSON structure exactly:\n"
            '{ "questions": [{"question": "string", "options": ["string","string","string","string"],\n'
            '  "correct_index": 0, "topic": "string"}] }'
        )

        user_prompt = f'Study Material:\n"""\n{text_content[:20000]}\n"""'

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
            raw_text = response.choices[0].message.content or "{}"
            data = extract_and_parse_json(raw_text)

            if not isinstance(data, dict):
                raise ValueError("Parsed JSON root is not an object.")

            raw_questions = data.get("questions", data.get("mcqs", []))
            valid_questions = []

            for item in raw_questions:
                if not isinstance(item, dict):
                    continue

                question_text = str(item.get("question", "")).strip()
                options = item.get("options", [])
                correct_idx = item.get("correct_index")
                topic = str(item.get("topic", "General")).strip() or "General"

                # Validation Rules:
                # 1. Non-empty question text
                # 2. Options must be a list of exactly 4 strings
                # 3. correct_index must be an integer between 0 and 3
                if (
                    question_text
                    and isinstance(options, list)
                    and len(options) == 4
                    and all(isinstance(opt, str) and opt.strip() for opt in options)
                    and isinstance(correct_idx, int)
                    and 0 <= correct_idx <= 3
                ):
                    valid_questions.append({
                        "question": question_text,
                        "options": [str(opt).strip() for opt in options],
                        "correct_index": correct_idx,
                        "topic": topic,
                    })
                else:
                    logger.warning(
                        f"Dropping malformed MCQ: question='{question_text[:30]}...', "
                        f"options_len={len(options) if isinstance(options, list) else 'non-list'}, "
                        f"correct_index={correct_idx}"
                    )

            return valid_questions
        except Exception as e:
            logger.error(f"MCQ generation failed: {e}")
            raise RuntimeError(f"LLM MCQ generation failed: {str(e)}")

    def generate_short_questions(self, text_content: str) -> List[Dict[str, Any]]:
        """Generates conceptual short-answer exam questions with model answers and topic labels."""
        system_prompt = (
            "You are a study assistant that creates short-answer exam questions from study material.\n"
            "Rules:\n"
            "- Use ONLY the provided content. Do not add outside facts.\n"
            "- Each question should require a 1-3 sentence answer, not a single word and not an essay.\n"
            "- Include a concise model answer for each question, based strictly on the material.\n"
            "- Decide the number of questions based on how much distinct, testable content exists\n"
            "  in the material.\n"
            "- Tag each question with a short topic label.\n"
            "- Return the output in the following JSON structure exactly:\n"
            '{ "questions": [{"question": "string", "model_answer": "string", "topic": "string"}] }'
        )

        user_prompt = f'Study Material:\n"""\n{text_content[:20000]}\n"""'

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
            raw_text = response.choices[0].message.content or "{}"
            data = extract_and_parse_json(raw_text)

            if not isinstance(data, dict):
                raise ValueError("Parsed JSON root is not an object.")

            raw_questions = data.get("questions", [])
            valid_questions = []

            for item in raw_questions:
                if not isinstance(item, dict):
                    continue

                q_text = str(item.get("question", "")).strip()
                ans_text = str(item.get("model_answer", item.get("sample_answer", ""))).strip()
                topic = str(item.get("topic", "General")).strip() or "General"

                if q_text and ans_text:
                    valid_questions.append({
                        "question": q_text,
                        "model_answer": ans_text,
                        "topic": topic,
                    })
                else:
                    logger.warning(f"Dropping incomplete short-answer question item: {item}")

            return valid_questions
        except Exception as e:
            logger.error(f"Short answer question generation failed: {e}")
            raise RuntimeError(f"LLM short-answer question generation failed: {str(e)}")

    def answer_question_with_context(self, question: str, context_chunks: List[str]) -> str:
        """Answers a user question based strictly on retrieved context chunks (RAG)."""
        retrieved_chunks = "\n\n---\n\n".join(context_chunks)

        system_prompt = (
            "You are a study assistant helping a student understand their uploaded course material.\n"
            "Rules:\n"
            "- Answer ONLY using the information in the provided context chunks.\n"
            "- If the answer is not present in the context, say: 'I couldn't find this in your uploaded material.' Do not guess or use outside knowledge.\n"
            "- Keep answers clear and exam-relevant, not overly long.\n"
            "- If helpful, quote the relevant line from the context to support your answer."
        )

        user_prompt = f'Context:\n"""\n{retrieved_chunks}\n"""\n\nQuestion: {question}'

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content
            return content.strip() if content else "I couldn't find this in your uploaded material."
        except Exception as e:
            logger.error(f"OpenAI ChatCompletion failure: {e}")
            raise RuntimeError(f"LLM Q&A generation failed: {str(e)}")
