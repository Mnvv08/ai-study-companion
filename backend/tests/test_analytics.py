"""
tests/test_analytics.py
───────────────────────
Unit/integration tests for Analytics/Weak Topic Detection endpoint (Phase 4).
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
        id="student-analytics-1",
        email="analytics_student@university.edu",
        name="Analytics Student",
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
        id="student-analytics-2",
        email="other_analytics@university.edu",
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
        id="doc-analytics-1",
        user_id=student_user.id,
        filename="analytics_material.pdf",
        file_path="/tmp/analytics.pdf",
        file_size_bytes=1024,
        file_type="pdf",
        status="processed",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()
    return doc


def test_weak_topics_unauthorized():
    """Verify that GET /analytics/weak-topics requires JWT authorization."""
    response = client.get("/analytics/weak-topics")
    assert response.status_code == 401


def test_weak_topics_no_history(auth_headers):
    """Verify that a user with no attempts returns an empty list, not an error."""
    response = client.get("/analytics/weak-topics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["weak_topics"] == []


def test_weak_topics_threshold_and_sorting(auth_headers, sample_document):
    """Verify that weak topics are correctly filtered by attempt threshold and sorted by accuracy."""
    db = TestingSessionLocal()
    # Create quiz
    quiz = Quiz(id="quiz-an", document_id=sample_document.id, quiz_type="mcq")
    db.add(quiz)

    # 1. Topic 'A': 3 attempts, 1 correct, 2 incorrect -> 33.33% accuracy
    # 2. Topic 'B': 4 attempts, 3 correct, 1 incorrect -> 75% accuracy
    # 3. Topic 'C': 2 attempts, 0 correct, 2 incorrect -> Excluded (attempts < 3)

    q_a1 = Question(id="q-a1", quiz_id="quiz-an", question_text="Q?", correct_answer="0", topic_tag="Topic A")
    q_a2 = Question(id="q-a2", quiz_id="quiz-an", question_text="Q?", correct_answer="0", topic_tag="Topic A")
    q_a3 = Question(id="q-a3", quiz_id="quiz-an", question_text="Q?", correct_answer="0", topic_tag="Topic A")

    q_b1 = Question(id="q-b1", quiz_id="quiz-an", question_text="Q?", correct_answer="0", topic_tag="Topic B")
    q_b2 = Question(id="q-b2", quiz_id="quiz-an", question_text="Q?", correct_answer="0", topic_tag="Topic B")
    q_b3 = Question(id="q-b3", quiz_id="quiz-an", question_text="Q?", correct_answer="0", topic_tag="Topic B")
    q_b4 = Question(id="q-b4", quiz_id="quiz-an", question_text="Q?", correct_answer="0", topic_tag="Topic B")

    q_c1 = Question(id="q-c1", quiz_id="quiz-an", question_text="Q?", correct_answer="0", topic_tag="Topic C")
    q_c2 = Question(id="q-c2", quiz_id="quiz-an", question_text="Q?", correct_answer="0", topic_tag="Topic C")

    db.add_all([q_a1, q_a2, q_a3, q_b1, q_b2, q_b3, q_b4, q_c1, q_c2])

    # Add attempt
    attempt = QuizAttempt(id="attempt-an", user_id="student-analytics-1", quiz_id="quiz-an", score=0.44)
    db.add(attempt)

    # Add attempt answers
    # Topic A: 1 correct (ans_a1), 2 incorrect (ans_a2, ans_a3)
    ans_a1 = AttemptAnswer(id="ans-a1", attempt_id="attempt-an", question_id="q-a1", student_answer="0", is_correct=True)
    ans_a2 = AttemptAnswer(id="ans-a2", attempt_id="attempt-an", question_id="q-a2", student_answer="1", is_correct=False)
    ans_a3 = AttemptAnswer(id="ans-a3", attempt_id="attempt-an", question_id="q-a3", student_answer="1", is_correct=False)

    # Topic B: 3 correct, 1 incorrect
    ans_b1 = AttemptAnswer(id="ans-b1", attempt_id="attempt-an", question_id="q-b1", student_answer="0", is_correct=True)
    ans_b2 = AttemptAnswer(id="ans-b2", attempt_id="attempt-an", question_id="q-b2", student_answer="0", is_correct=True)
    ans_b3 = AttemptAnswer(id="ans-b3", attempt_id="attempt-an", question_id="q-b3", student_answer="0", is_correct=True)
    ans_b4 = AttemptAnswer(id="ans-b4", attempt_id="attempt-an", question_id="q-b4", student_answer="1", is_correct=False)

    # Topic C: 2 incorrect (no correct)
    ans_c1 = AttemptAnswer(id="ans-c1", attempt_id="attempt-an", question_id="q-c1", student_answer="1", is_correct=False)
    ans_c2 = AttemptAnswer(id="ans-c2", attempt_id="attempt-an", question_id="q-c2", student_answer="1", is_correct=False)

    db.add_all([ans_a1, ans_a2, ans_a3, ans_b1, ans_b2, ans_b3, ans_b4, ans_c1, ans_c2])
    db.commit()
    db.close()

    # Query endpoint
    response = client.get("/analytics/weak-topics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Topic C must be excluded because it only has 2 attempts (threshold is 3)
    assert len(data["weak_topics"]) == 2

    # Weakest first (Topic A: 33.33% < Topic B: 75%)
    assert data["weak_topics"][0]["topic"] == "Topic A"
    assert data["weak_topics"][0]["accuracy_percentage"] == 33.33
    assert data["weak_topics"][0]["total_attempted"] == 3

    assert data["weak_topics"][1]["topic"] == "Topic B"
    assert data["weak_topics"][1]["accuracy_percentage"] == 75.0
    assert data["weak_topics"][1]["total_attempted"] == 4


def test_weak_topics_ownership_isolation(auth_headers, other_auth_headers, sample_document):
    """Verify that a user only sees metrics generated by their own attempts."""
    db = TestingSessionLocal()
    quiz = Quiz(id="quiz-iso", document_id=sample_document.id, quiz_type="mcq")
    db.add(quiz)

    q1 = Question(id="q-iso1", quiz_id="quiz-iso", question_text="Q?", correct_answer="0", topic_tag="Topic ISO")
    q2 = Question(id="q-iso2", quiz_id="quiz-iso", question_text="Q?", correct_answer="0", topic_tag="Topic ISO")
    q3 = Question(id="q-iso3", quiz_id="quiz-iso", question_text="Q?", correct_answer="0", topic_tag="Topic ISO")
    db.add_all([q1, q2, q3])

    # User 2 attempts quiz-iso (which belongs to user 1's document, but that doesn't prevent attempt creation by user 2 in DB context)
    attempt_other = QuizAttempt(id="attempt-other-iso", user_id="student-analytics-2", quiz_id="quiz-iso", score=1.0)
    db.add(attempt_other)

    ans1 = AttemptAnswer(id="ans-iso1", attempt_id="attempt-other-iso", question_id="q-iso1", student_answer="0", is_correct=True)
    ans2 = AttemptAnswer(id="ans-iso2", attempt_id="attempt-other-iso", question_id="q-iso2", student_answer="0", is_correct=True)
    ans3 = AttemptAnswer(id="ans-iso3", attempt_id="attempt-other-iso", question_id="q-iso3", student_answer="0", is_correct=True)
    db.add_all([ans1, ans2, ans3])
    db.commit()
    db.close()

    # Query endpoint as user 1 (should return empty list because user 1 has no attempts)
    response = client.get("/analytics/weak-topics", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["weak_topics"] == []

    # Query endpoint as user 2 (should return Topic ISO with 100% accuracy)
    response2 = client.get("/analytics/weak-topics", headers=other_auth_headers)
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["weak_topics"]) == 1
    assert data2["weak_topics"][0]["topic"] == "Topic ISO"
    assert data2["weak_topics"][0]["accuracy_percentage"] == 100.0


def test_recommendations_unauthorized():
    """Verify that GET /analytics/recommendations requires JWT authorization."""
    response = client.get("/analytics/recommendations")
    assert response.status_code == 401


def test_recommendations_no_history(auth_headers):
    """Verify that a user with no history returns empty recommendations list."""
    response = client.get("/analytics/recommendations", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["recommendations"] == []


def test_recommendations_success(auth_headers, sample_document):
    """Verify that revision recommendations returns the top 3 weakest topics with formatted reason and document info."""
    db = TestingSessionLocal()
    quiz = Quiz(id="quiz-rec", document_id=sample_document.id, quiz_type="mcq")
    db.add(quiz)

    # We create 4 topics so we can verify only the top 3 weakest are recommended
    # Topic 1: 3 attempts, 0 correct -> 0% accuracy
    # Topic 2: 3 attempts, 1 correct -> 33.33% accuracy
    # Topic 3: 3 attempts, 2 correct -> 66.67% accuracy
    # Topic 4: 3 attempts, 3 correct -> 100% accuracy (excluded from top 3 weakest)

    questions = []
    # Topic 1
    questions.append(Question(id="q-t1-1", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 1"))
    questions.append(Question(id="q-t1-2", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 1"))
    questions.append(Question(id="q-t1-3", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 1"))
    # Topic 2
    questions.append(Question(id="q-t2-1", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 2"))
    questions.append(Question(id="q-t2-2", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 2"))
    questions.append(Question(id="q-t2-3", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 2"))
    # Topic 3
    questions.append(Question(id="q-t3-1", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 3"))
    questions.append(Question(id="q-t3-2", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 3"))
    questions.append(Question(id="q-t3-3", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 3"))
    # Topic 4
    questions.append(Question(id="q-t4-1", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 4"))
    questions.append(Question(id="q-t4-2", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 4"))
    questions.append(Question(id="q-t4-3", quiz_id="quiz-rec", question_text="Q?", correct_answer="0", topic_tag="Topic 4"))

    db.add_all(questions)

    # Add attempt
    attempt = QuizAttempt(id="attempt-rec", user_id="student-analytics-1", quiz_id="quiz-rec", score=0.5)
    db.add(attempt)

    # Topic 1: 0 correct
    ans1 = AttemptAnswer(id="ans-t1-1", attempt_id="attempt-rec", question_id="q-t1-1", student_answer="1", is_correct=False)
    ans2 = AttemptAnswer(id="ans-t1-2", attempt_id="attempt-rec", question_id="q-t1-2", student_answer="1", is_correct=False)
    ans3 = AttemptAnswer(id="ans-t1-3", attempt_id="attempt-rec", question_id="q-t1-3", student_answer="1", is_correct=False)
    # Topic 2: 1 correct
    ans4 = AttemptAnswer(id="ans-t2-1", attempt_id="attempt-rec", question_id="q-t2-1", student_answer="0", is_correct=True)
    ans5 = AttemptAnswer(id="ans-t2-2", attempt_id="attempt-rec", question_id="q-t2-2", student_answer="1", is_correct=False)
    ans6 = AttemptAnswer(id="ans-t2-3", attempt_id="attempt-rec", question_id="q-t2-3", student_answer="1", is_correct=False)
    # Topic 3: 2 correct
    ans7 = AttemptAnswer(id="ans-t3-1", attempt_id="attempt-rec", question_id="q-t3-1", student_answer="0", is_correct=True)
    ans8 = AttemptAnswer(id="ans-t3-2", attempt_id="attempt-rec", question_id="q-t3-2", student_answer="0", is_correct=True)
    ans9 = AttemptAnswer(id="ans-t3-3", attempt_id="attempt-rec", question_id="q-t3-3", student_answer="1", is_correct=False)
    # Topic 4: 3 correct
    ans10 = AttemptAnswer(id="ans-t4-1", attempt_id="attempt-rec", question_id="q-t4-1", student_answer="0", is_correct=True)
    ans11 = AttemptAnswer(id="ans-t4-2", attempt_id="attempt-rec", question_id="q-t4-2", student_answer="0", is_correct=True)
    ans12 = AttemptAnswer(id="ans-t4-3", attempt_id="attempt-rec", question_id="q-t4-3", student_answer="0", is_correct=True)

    db.add_all([ans1, ans2, ans3, ans4, ans5, ans6, ans7, ans8, ans9, ans10, ans11, ans12])
    db.commit()
    db.close()

    response = client.get("/analytics/recommendations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    # Should only recommend top 3 weakest (Topic 1, 2, 3)
    recs = data["recommendations"]
    assert len(recs) == 3

    # Topic 1 should be first (weakest, 0% accuracy)
    assert recs[0]["topic"] == "Topic 1"
    assert recs[0]["reason"] == "Only 0.0% accuracy across 3 questions"
    assert recs[0]["document_id"] == sample_document.id
    assert recs[0]["document_filename"] == sample_document.filename

    # Topic 2 should be second (33.33% accuracy)
    assert recs[1]["topic"] == "Topic 2"
    assert recs[1]["reason"] == "Only 33.33% accuracy across 3 questions"

    # Topic 3 should be third (66.67% accuracy)
    assert recs[2]["topic"] == "Topic 3"
    assert recs[2]["reason"] == "Only 66.67% accuracy across 3 questions"

