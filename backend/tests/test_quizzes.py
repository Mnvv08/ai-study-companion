"""
tests/test_quizzes.py
─────────────────────
Unit/integration tests for Quiz creation, persistence, and attempt retrieval (Phase 3).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from app.models.file import Document
from app.models.quiz import Quiz, Question, QuizAttempt, AttemptAnswer
from app.services.llm_client import LLMClientService

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def student_user():
    db = TestingSessionLocal()
    user = User(
        id="student-quiz-1",
        email="quiz_student@university.edu",
        name="Quiz Student",
        hashed_password=get_password_hash("pass123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def other_user():
    db = TestingSessionLocal()
    user = User(
        id="student-quiz-2",
        email="other_quiz@university.edu",
        name="Other Student",
        hashed_password=get_password_hash("pass123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def auth_headers(student_user):
    token = create_access_token(data={"sub": student_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user):
    token = create_access_token(data={"sub": other_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_document(student_user):
    db = TestingSessionLocal()
    doc = Document(
        id="doc-quiz-101",
        user_id=student_user.id,
        filename="quiz_material.pdf",
        file_path="/tmp/quiz.pdf",
        file_size_bytes=2048,
        file_type="pdf",
        status="processed",
        extracted_text="Mitochondria are the powerhouse of the cell. They generate ATP.",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()
    return doc


def test_mcq_generation_persists_quiz_and_questions(auth_headers, sample_document, monkeypatch):
    """Verify that generate MCQs persists quiz/questions and returns IDs."""
    mock_mcqs = [
        {
            "question": "What is the powerhouse of the cell?",
            "options": ["Mitochondria", "Nucleus", "Ribosome", "Lysosome"],
            "correct_index": 0,
            "topic": "Cell Biology"
        }
    ]

    monkeypatch.setattr(
        LLMClientService,
        "generate_mcqs",
        lambda self, text_content, *args, **kwargs: mock_mcqs
    )

    response = client.post(
        "/mcqs/generate",
        headers=auth_headers,
        json={"document_id": sample_document.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert "quiz_id" in data
    assert len(data["questions"]) == 1

    question_data = data["questions"][0]
    assert "id" in question_data
    assert question_data["quiz_id"] == data["quiz_id"]
    assert question_data["question"] == "What is the powerhouse of the cell?"
    assert question_data["correct_index"] == 0

    # Verify database state
    db = TestingSessionLocal()
    quiz = db.query(Quiz).filter(Quiz.id == data["quiz_id"]).first()
    assert quiz is not None
    assert quiz.quiz_type == "mcq"
    assert len(quiz.questions) == 1
    assert quiz.questions[0].id == question_data["id"]
    assert quiz.questions[0].correct_answer == "0"
    db.close()


def test_short_answer_generation_persists_quiz_and_questions(auth_headers, sample_document, monkeypatch):
    """Verify that generate short-answer questions persists quiz/questions and returns IDs."""
    mock_questions = [
        {
            "question": "Describe the main function of Mitochondria.",
            "model_answer": "They generate adenosine triphosphate (ATP).",
            "topic": "Cell Biology"
        }
    ]

    monkeypatch.setattr(
        LLMClientService,
        "generate_short_questions",
        lambda self, text_content, *args, **kwargs: mock_questions
    )

    response = client.post(
        "/short-answer/generate",
        headers=auth_headers,
        json={"document_id": sample_document.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert "quiz_id" in data
    assert len(data["questions"]) == 1

    question_data = data["questions"][0]
    assert "id" in question_data
    assert question_data["quiz_id"] == data["quiz_id"]
    assert question_data["model_answer"] == "They generate adenosine triphosphate (ATP)."

    # Verify database state
    db = TestingSessionLocal()
    quiz = db.query(Quiz).filter(Quiz.id == data["quiz_id"]).first()
    assert quiz is not None
    assert quiz.quiz_type == "short_answer"
    assert len(quiz.questions) == 1
    assert quiz.questions[0].correct_answer == "They generate adenosine triphosphate (ATP)."
    db.close()


def test_get_quiz_hides_correct_answers(auth_headers, sample_document):
    """Verify that GET /quizzes/{quiz_id} returns questions without correct answers."""
    db = TestingSessionLocal()
    # Create quiz in DB
    quiz = Quiz(
        id="test-quiz-abc",
        document_id=sample_document.id,
        quiz_type="mcq"
    )
    db.add(quiz)
    q1 = Question(
        id="q-1",
        quiz_id="test-quiz-abc",
        question_text="Q1?",
        options=["A", "B", "C", "D"],
        correct_answer="2",
        topic_tag="Tag"
    )
    db.add(q1)
    db.commit()
    db.close()

    # Get quiz via endpoint
    response = client.get(
        "/quizzes/test-quiz-abc",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-quiz-abc"
    assert data["quiz_type"] == "mcq"
    assert len(data["questions"]) == 1

    fetched_question = data["questions"][0]
    assert fetched_question["id"] == "q-1"
    assert fetched_question["quiz_id"] == "test-quiz-abc"
    assert fetched_question["question_text"] == "Q1?"
    assert fetched_question["options"] == ["A", "B", "C", "D"]
    # Ensure correct answer/index is NOT in the response!
    assert "correct_answer" not in fetched_question
    assert "correct_index" not in fetched_question


def test_get_quiz_other_user_returns_404(auth_headers, other_auth_headers, sample_document):
    """Verify that getting a quiz of another user returns 404."""
    db = TestingSessionLocal()
    quiz = Quiz(
        id="test-quiz-other",
        document_id=sample_document.id,
        quiz_type="mcq"
    )
    db.add(quiz)
    db.commit()
    db.close()

    # Request with other user headers
    response = client.get(
        "/quizzes/test-quiz-other",
        headers=other_auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Quiz not found."


def test_get_quiz_non_existent_returns_404(auth_headers):
    """Verify that requesting non-existent quiz returns 404."""
    response = client.get(
        "/quizzes/non-existent-quiz-id",
        headers=auth_headers
    )
    assert response.status_code == 404


def test_submit_mcq_quiz_success(auth_headers, sample_document):
    """Verify that submitting MCQ answers computes correct score and persists attempts."""
    db = TestingSessionLocal()
    quiz = Quiz(
        id="mcq-quiz-submit",
        document_id=sample_document.id,
        quiz_type="mcq"
    )
    db.add(quiz)
    q1 = Question(
        id="mq-1",
        quiz_id="mcq-quiz-submit",
        question_text="Q1?",
        options=["A", "B", "C", "D"],
        correct_answer="1",  # Index 1
        topic_tag="Biology"
    )
    q2 = Question(
        id="mq-2",
        quiz_id="mcq-quiz-submit",
        question_text="Q2?",
        options=["A", "B", "C", "D"],
        correct_answer="3",  # Index 3
        topic_tag="Chemistry"
    )
    db.add(q1)
    db.add(q2)
    db.commit()
    db.close()

    # Submit 1 correct, 1 incorrect
    payload = {
        "answers": [
            {"question_id": "mq-1", "student_answer": "1"},  # Correct
            {"question_id": "mq-2", "student_answer": "0"}   # Incorrect
        ]
    }

    response = client.post(
        "/quizzes/mcq-quiz-submit/submit",
        headers=auth_headers,
        json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert "attempt_id" in data
    assert data["quiz_id"] == "mcq-quiz-submit"
    assert data["score"] == 0.5
    assert data["questions_count"] == 2
    assert data["correct_count"] == 1
    assert len(data["feedback"]) == 2

    # Check feedback
    feedback_q1 = next(item for item in data["feedback"] if item["question_id"] == "mq-1")
    assert feedback_q1["is_correct"] is True
    assert feedback_q1["student_answer"] == "1"
    assert feedback_q1["correct_answer"] == "1"

    feedback_q2 = next(item for item in data["feedback"] if item["question_id"] == "mq-2")
    assert feedback_q2["is_correct"] is False
    assert feedback_q2["student_answer"] == "0"
    assert feedback_q2["correct_answer"] == "3"

    # Verify database state
    db = TestingSessionLocal()
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == data["attempt_id"]).first()
    assert attempt is not None
    assert attempt.score == 0.5
    assert len(attempt.answers) == 2
    db.close()


def test_submit_short_answer_quiz_success(auth_headers, sample_document):
    """Verify that submitting short-answer questions does keyword matching."""
    db = TestingSessionLocal()
    quiz = Quiz(
        id="sa-quiz-submit",
        document_id=sample_document.id,
        quiz_type="short_answer"
    )
    db.add(quiz)
    q1 = Question(
        id="sa-1",
        quiz_id="sa-quiz-submit",
        question_text="What is ATP?",
        options=None,
        correct_answer="Adenosine Triphosphate",
        topic_tag="Biology"
    )
    db.add(q1)
    db.commit()
    db.close()

    # Submit answer containing keyword (substring)
    payload = {
        "answers": [
            {"question_id": "sa-1", "student_answer": "It is adenosine triphosphate"}
        ]
    }

    response = client.post(
        "/quizzes/sa-quiz-submit/submit",
        headers=auth_headers,
        json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 1.0
    assert data["correct_count"] == 1
    assert data["feedback"][0]["is_correct"] is True


def test_submit_quiz_other_user_document_404(other_auth_headers, sample_document):
    """Verify that submitting answers to another user's quiz returns 404."""
    db = TestingSessionLocal()
    quiz = Quiz(
        id="sa-quiz-other-submit",
        document_id=sample_document.id,
        quiz_type="short_answer"
    )
    db.add(quiz)
    db.commit()
    db.close()

    payload = {
        "answers": []
    }

    response = client.post(
        "/quizzes/sa-quiz-other-submit/submit",
        headers=other_auth_headers,
        json=payload
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Quiz not found."

