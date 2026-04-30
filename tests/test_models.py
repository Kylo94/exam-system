"""
模型单元测试
"""
import pytest
import pytest_asyncio
from app.models.user import User
from app.models.subject import Subject
from app.models.level import Level
from app.models.exam import Exam
from app.models.question import Question


@pytest_asyncio.fixture(scope="function", autouse=True)
async def test_db():
    """初始化测试数据库"""
    from tortoise import Tortoise
    
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["app.models"]}
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_user_creation(test_db):
    """测试用户创建"""
    user = await User.create(
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        role="student",
        is_active=True
    )
    
    assert user.id is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.role == "student"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_user_default_values(test_db):
    """测试用户默认值"""
    user = await User.create(
        username="defaultuser",
        email="default@example.com",
        password_hash="hashed",
        role="student"
    )
    
    assert user.is_active is True
    assert user.last_login_at is None


@pytest.mark.asyncio
async def test_subject_creation(test_db):
    """测试科目创建"""
    subject = await Subject.create(
        name="数学",
        description="数学测试"
    )
    
    assert subject.id is not None
    assert subject.name == "数学"


@pytest.mark.asyncio
async def test_level_creation(test_db):
    """测试难度创建"""
    subject = await Subject.create(name="数学", code="MATH")
    level = await Level.create(
        name="基础",
        description="基础难度",
        subject=subject
    )

    assert level.id is not None
    assert level.name == "基础"
    assert level.subject_id == subject.id


@pytest.mark.asyncio
async def test_exam_creation(test_db):
    """测试试卷创建"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(
        username="teacher",
        email="teacher@example.com",
        password_hash="hashed",
        role="teacher"
    )
    
    exam = await Exam.create(
        title="期末考试",
        subject=subject,
        creator=teacher,
        total_points=100,
        duration_minutes=60,
        pass_score=60,
        is_published=True
    )
    
    assert exam.id is not None
    assert exam.title == "期末考试"
    assert exam.total_points == 100
    assert exam.duration_minutes == 60
    assert exam.pass_score == 60
    assert exam.is_published is True


@pytest.mark.asyncio
async def test_exam_without_time_limits(test_db):
    """测试试卷无时间限制"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(
        username="teacher2",
        email="teacher2@example.com",
        password_hash="hashed",
        role="teacher"
    )
    
    exam = await Exam.create(
        title="随时测试",
        subject=subject,
        creator=teacher,
        is_published=True
    )
    
    # 确认没有 start_time 和 end_time
    assert not hasattr(exam, 'start_time') or exam.start_time is None
    assert not hasattr(exam, 'end_time') or exam.end_time is None


@pytest.mark.asyncio
async def test_question_creation(test_db):
    """测试题目创建"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(
        username="teacher3",
        email="teacher3@example.com",
        password_hash="hashed",
        role="teacher"
    )
    exam = await Exam.create(
        title="测试试卷",
        subject=subject,
        creator=teacher
    )
    
    question = await Question.create(
        exam=exam,
        type="single_choice",
        content="1+1=?",
        options={"A": "1", "B": "2", "C": "3", "D": "4"},
        correct_answer="B",
        points=10,
        explanation="1+1=2"
    )
    
    assert question.id is not None
    assert question.type == "single_choice"
    assert question.content == "1+1=?"
    assert question.points == 10


@pytest.mark.asyncio
async def test_question_check_answer(test_db):
    """测试题目答案检查"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(
        username="teacher4",
        email="teacher4@example.com",
        password_hash="hashed",
        role="teacher"
    )
    exam = await Exam.create(
        title="测试试卷2",
        subject=subject,
        creator=teacher
    )
    
    question = await Question.create(
        exam=exam,
        type="single_choice",
        content="2+2=?",
        options={"A": "3", "B": "4", "C": "5", "D": "6"},
        correct_answer="B",
        points=10
    )
    
    assert question.check_answer("B") is True
    assert question.check_answer("A") is False
    assert question.check_answer("b") is True  # 大小写不敏感
