"""
tests/test_review.py
────────────────────
Integration tests for spaced repetition: the /review endpoints, and the
wiring that turns a quiz submission into schedule updates.

The scheduling arithmetic itself is covered in test_scheduler.py. What's
tested here is the database and HTTP layer around it — that submitting a quiz
creates the right rows, that per-user isolation holds, and that "due" means
what it says.
"""

from datetime import datetime, timedelta, timezone

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
from app.models.quiz import Quiz, Question
from app.models.review import TopicReview

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
def student():
    """
    Create the student and return the id, not the ORM object.

    The session is closed here, which would leave a returned User detached —
    touching any attribute afterwards raises DetachedInstanceError. Returning
    the plain id sidesteps that entirely.
    """
    db = TestingSessionLocal()
    db.add(
        User(
            id="student-review-1",
            email="review_student@university.edu",
            name="Review Student",
            hashed_password=get_password_hash("pass123"),
        )
    )
    db.commit()
    db.close()
    return "student-review-1"


@pytest.fixture
def auth_headers(student):
    token = create_access_token(data={"sub": student})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mcq_quiz(student):
    """
    A four-question MCQ quiz across two topics, two questions each.

    Two topics lets the tests show that one can pass while the other fails
    in the same attempt — the behaviour that makes per-topic scheduling
    worth having over a single overall score.
    """
    db = TestingSessionLocal()
    doc = Document(
        id="doc-review-1",
        user_id=student,
        filename="dbms.pdf",
        file_path="/tmp/dbms.pdf",
        file_size_bytes=2048,
        file_type="pdf",
        extracted_text="Normalization and transaction isolation notes.",
        status="processed",
    )
    db.add(doc)

    quiz = Quiz(id="quiz-review-1", document_id=doc.id, quiz_type="mcq")
    db.add(quiz)

    for idx, (qid, topic) in enumerate(
        [
            ("q-norm-1", "Normalization"),
            ("q-norm-2", "Normalization"),
            ("q-iso-1", "Transaction Isolation"),
            ("q-iso-2", "Transaction Isolation"),
        ]
    ):
        db.add(
            Question(
                id=qid,
                quiz_id=quiz.id,
                question_text=f"Question {idx}",
                options=["A", "B", "C", "D"],
                correct_answer="0",
                topic_tag=topic,
            )
        )
    db.commit()
    db.close()
    return quiz


def _submit(auth_headers, answers):
    return client.post(
        "/api/v1/quizzes/quiz-review-1/submit",
        headers=auth_headers,
        json={"answers": answers},
    )


ALL_CORRECT = [
    {"question_id": "q-norm-1", "student_answer": "0"},
    {"question_id": "q-norm-2", "student_answer": "0"},
    {"question_id": "q-iso-1", "student_answer": "0"},
    {"question_id": "q-iso-2", "student_answer": "0"},
]

NORM_RIGHT_ISO_WRONG = [
    {"question_id": "q-norm-1", "student_answer": "0"},
    {"question_id": "q-norm-2", "student_answer": "0"},
    {"question_id": "q-iso-1", "student_answer": "3"},
    {"question_id": "q-iso-2", "student_answer": "3"},
]


# ── submission creates schedules ─────────────────────────────────────

def test_submitting_a_quiz_creates_one_schedule_per_topic(auth_headers, mcq_quiz):
    assert _submit(auth_headers, ALL_CORRECT).status_code == 200

    db = TestingSessionLocal()
    rows = db.query(TopicReview).filter_by(user_id="student-review-1").all()
    db.close()

    assert len(rows) == 2
    assert {r.topic for r in rows} == {"Normalization", "Transaction Isolation"}


def test_topics_are_scheduled_independently_within_one_attempt(auth_headers, mcq_quiz):
    """
    The point of per-topic scheduling: one attempt can pass one topic and
    fail another, and they get different futures.
    """
    assert _submit(auth_headers, NORM_RIGHT_ISO_WRONG).status_code == 200

    db = TestingSessionLocal()
    rows = {r.topic: r for r in db.query(TopicReview).all()}
    db.close()

    assert rows["Normalization"].repetitions == 1
    assert rows["Transaction Isolation"].repetitions == 0


def test_resubmitting_updates_the_existing_row_rather_than_duplicating(
    auth_headers, mcq_quiz
):
    _submit(auth_headers, ALL_CORRECT)
    _submit(auth_headers, ALL_CORRECT)

    db = TestingSessionLocal()
    rows = db.query(TopicReview).filter_by(topic="Normalization").all()
    db.close()

    assert len(rows) == 1
    assert rows[0].total_reviews == 2
    assert rows[0].repetitions == 2


def test_failing_a_previously_passed_topic_records_a_lapse(auth_headers, mcq_quiz):
    _submit(auth_headers, ALL_CORRECT)
    _submit(auth_headers, NORM_RIGHT_ISO_WRONG)

    db = TestingSessionLocal()
    iso = db.query(TopicReview).filter_by(topic="Transaction Isolation").one()
    db.close()

    assert iso.lapses == 1
    assert iso.repetitions == 0


def test_failing_a_never_passed_topic_is_not_a_lapse(auth_headers, mcq_quiz):
    """Never having learned something is different from forgetting it."""
    _submit(auth_headers, NORM_RIGHT_ISO_WRONG)

    db = TestingSessionLocal()
    iso = db.query(TopicReview).filter_by(topic="Transaction Isolation").one()
    db.close()

    assert iso.lapses == 0


# ── GET /review/due ──────────────────────────────────────────────────

def test_due_is_empty_for_a_student_who_has_not_studied(auth_headers):
    res = client.get("/api/v1/review/due", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["due_count"] == 0
    assert body["total_tracked"] == 0
    assert body["items"] == []


def test_freshly_scheduled_topics_are_not_due_yet(auth_headers, mcq_quiz):
    """
    Everything scheduled today is due tomorrow at the earliest, so a student
    who just finished a quiz shouldn't be told to redo it immediately.
    """
    _submit(auth_headers, ALL_CORRECT)

    body = client.get("/api/v1/review/due", headers=auth_headers).json()
    assert body["due_count"] == 0
    assert body["total_tracked"] == 2


def test_overdue_topics_appear_most_overdue_first(auth_headers, mcq_quiz):
    _submit(auth_headers, ALL_CORRECT)

    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()
    db.query(TopicReview).filter_by(topic="Normalization").update(
        {"due_at": now - timedelta(days=2)}
    )
    db.query(TopicReview).filter_by(topic="Transaction Isolation").update(
        {"due_at": now - timedelta(days=9)}
    )
    db.commit()
    db.close()

    body = client.get("/api/v1/review/due", headers=auth_headers).json()
    assert body["due_count"] == 2
    assert [i["topic"] for i in body["items"]] == [
        "Transaction Isolation",
        "Normalization",
    ]
    assert body["items"][0]["days_overdue"] == 9


def test_due_respects_the_limit_parameter(auth_headers, mcq_quiz):
    _submit(auth_headers, ALL_CORRECT)

    past = datetime.now(timezone.utc) - timedelta(days=1)
    db = TestingSessionLocal()
    db.query(TopicReview).update({"due_at": past})
    db.commit()
    db.close()

    body = client.get("/api/v1/review/due?limit=1", headers=auth_headers).json()
    assert body["due_count"] == 1
    assert body["total_tracked"] == 2


# ── GET /review/schedule ─────────────────────────────────────────────

def test_schedule_lists_all_topics_including_ones_not_yet_due(
    auth_headers, mcq_quiz
):
    _submit(auth_headers, ALL_CORRECT)

    res = client.get("/api/v1/review/schedule", headers=auth_headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    assert all(i["days_overdue"] == 0 for i in items)
    assert {i["mastery"] for i in items} == {"shaky"}


def test_mastery_label_reflects_a_long_interval(auth_headers, mcq_quiz):
    _submit(auth_headers, ALL_CORRECT)

    db = TestingSessionLocal()
    db.query(TopicReview).filter_by(topic="Normalization").update(
        {"interval_days": 60, "repetitions": 5}
    )
    db.commit()
    db.close()

    items = client.get("/api/v1/review/schedule", headers=auth_headers).json()
    norm = next(i for i in items if i["topic"] == "Normalization")
    assert norm["mastery"] == "solid"


# ── isolation and auth ───────────────────────────────────────────────

def test_one_students_schedule_is_invisible_to_another(auth_headers, mcq_quiz):
    _submit(auth_headers, ALL_CORRECT)

    db = TestingSessionLocal()
    other = User(
        id="student-review-2",
        email="other@university.edu",
        name="Other Student",
        hashed_password=get_password_hash("pass123"),
    )
    db.add(other)
    db.commit()
    db.close()

    other_token = create_access_token(data={"sub": "student-review-2"})
    other_headers = {"Authorization": f"Bearer {other_token}"}
    body = client.get("/api/v1/review/due", headers=other_headers).json()
    assert body["total_tracked"] == 0


@pytest.mark.parametrize("path", ["/api/v1/review/due", "/api/v1/review/schedule"])
def test_review_endpoints_require_authentication(path):
    assert client.get(path).status_code in (401, 403)
