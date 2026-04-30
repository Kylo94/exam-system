"""服务层单元测试"""
import pytest
import pytest_asyncio
from app.models.user import User
from app.models.subject import Subject
from app.models.level import Level
from app.models.exam import Exam
from app.models.question import Question
from app.models.knowledge_point import KnowledgePoint
from app.services.user_service import UserService
from app.services.subject_service import SubjectService
from app.services.exam_service import ExamService
from app.services.question_service import QuestionService
from app.services.exceptions import NotFoundException, ValidationException, DuplicateException


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


# ==================== UserService Tests ====================

@pytest.mark.asyncio
async def test_get_user_or_404_exists(test_db):
    """测试获取存在的用户"""
    user = await User.create(
        username="testuser",
        email="test@example.com",
        password_hash="hash",
        role="student"
    )
    result = await UserService.get_user_or_404(user.id)
    assert result.id == user.id
    assert result.username == "testuser"


@pytest.mark.asyncio
async def test_get_user_or_404_not_exists(test_db):
    """测试获取不存在的用户"""
    with pytest.raises(NotFoundException) as exc:
        await UserService.get_user_or_404(9999)
    assert "用户" in str(exc.value)


@pytest.mark.asyncio
async def test_get_by_username(test_db):
    """测试根据用户名获取用户"""
    await User.create(username="findme", email="find@example.com", password_hash="hash", role="student")
    result = await UserService.get_by_username("findme")
    assert result is not None
    assert result.username == "findme"

    result_none = await UserService.get_by_username("notexist")
    assert result_none is None


@pytest.mark.asyncio
async def test_get_by_email(test_db):
    """测试根据邮箱获取用户"""
    await User.create(username="user1", email="unique@example.com", password_hash="hash", role="student")
    result = await UserService.get_by_email("unique@example.com")
    assert result is not None
    assert result.email == "unique@example.com"

    result_none = await UserService.get_by_email("notexist@example.com")
    assert result_none is None


@pytest.mark.asyncio
async def test_create_user_success(test_db):
    """测试成功创建用户"""
    user = await UserService.create_user(
        username="newuser",
        email="new@example.com",
        password="password123",
        role="student"
    )
    assert user.id is not None
    assert user.username == "newuser"
    assert user.email == "new@example.com"
    assert user.role == "student"
    assert user.password_hash != "password123"  # 应该被哈希化


@pytest.mark.asyncio
async def test_create_user_duplicate_username(test_db):
    """测试创建重复用户名"""
    await User.create(username="existing", email="a@example.com", password_hash="hash", role="student")
    with pytest.raises(DuplicateException):
        await UserService.create_user("existing", "b@example.com", "pass", "student")


@pytest.mark.asyncio
async def test_create_user_duplicate_email(test_db):
    """测试创建重复邮箱"""
    await User.create(username="existing2", email="duplicate@example.com", password_hash="hash", role="student")
    with pytest.raises(DuplicateException):
        await UserService.create_user("newuser", "duplicate@example.com", "pass", "student")


@pytest.mark.asyncio
async def test_create_user_invalid_role(test_db):
    """测试创建无效角色用户"""
    with pytest.raises(ValidationException):
        await UserService.create_user("user", "user@example.com", "pass", "invalid_role")


@pytest.mark.asyncio
async def test_toggle_active(test_db):
    """测试切换用户激活状态"""
    user = await User.create(
        username="toggleuser",
        email="toggle@example.com",
        password_hash="hash",
        role="student",
        is_active=True
    )
    assert user.is_active is True

    result = await UserService.toggle_active(user.id, current_user_id=999)  # 999是模拟的当前用户ID
    assert result.is_active is False

    result2 = await UserService.toggle_active(user.id, current_user_id=999)
    assert result2.is_active is True


@pytest.mark.asyncio
async def test_toggle_active_self(test_db):
    """测试不能禁用自己"""
    user = await User.create(
        username="selfuser",
        email="self@example.com",
        password_hash="hash",
        role="admin"
    )
    with pytest.raises(ValidationException) as exc:
        await UserService.toggle_active(user.id, user.id)
    assert "不能禁用自己" in str(exc.value)


@pytest.mark.asyncio
async def test_change_role(test_db):
    """测试修改用户角色"""
    user = await User.create(
        username="roleuser",
        email="role@example.com",
        password_hash="hash",
        role="student"
    )
    result = await UserService.change_role(user.id, "teacher")
    assert result.role == "teacher"


@pytest.mark.asyncio
async def test_change_role_invalid(test_db):
    """测试修改为无效角色"""
    user = await User.create(
        username="invalidrole",
        email="invalid@example.com",
        password_hash="hash",
        role="student"
    )
    with pytest.raises(ValidationException):
        await UserService.change_role(user.id, "invalid")


@pytest.mark.asyncio
async def test_list_users_pagination(test_db):
    """测试用户分页查询"""
    # 创建10个用户
    for i in range(10):
        await User.create(
            username=f"user{i}",
            email=f"user{i}@example.com",
            password_hash="hash",
            role="student"
        )

    # 测试分页
    users, total = await UserService.list_users(page=1, page_size=5)
    assert len(users) == 5
    assert total == 10

    users2, total2 = await UserService.list_users(page=2, page_size=5)
    assert len(users2) == 5
    assert total2 == 10


@pytest.mark.asyncio
async def test_list_users_filter_by_role(test_db):
    """测试按角色筛选用户"""
    await User.create(username="admin1", email="admin1@example.com", password_hash="hash", role="admin")
    await User.create(username="teacher1", email="teacher1@example.com", password_hash="hash", role="teacher")
    await User.create(username="student1", email="student1@example.com", password_hash="hash", role="student")

    users, total = await UserService.list_users(role="teacher")
    assert total == 1
    assert users[0].role == "teacher"


@pytest.mark.asyncio
async def test_list_users_search(test_db):
    """测试搜索用户"""
    await User.create(username="john_doe", email="john@example.com", password_hash="hash", role="student")
    await User.create(username="jane_doe", email="jane@example.com", password_hash="hash", role="student")

    users, total = await UserService.list_users(search="john")
    assert total == 1
    assert users[0].username == "john_doe"


# ==================== SubjectService Tests ====================

@pytest.mark.asyncio
async def test_get_subject_or_404(test_db):
    """测试获取科目"""
    subject = await Subject.create(name="数学", code="MATH")
    result = await SubjectService.get_subject_or_404(subject.id)
    assert result.id == subject.id


@pytest.mark.asyncio
async def test_create_subject_with_levels(test_db):
    """测试创建科目（同时创建等级）"""
    subject = await SubjectService.create_subject("英语", description="英语科目", level_count=3)

    assert subject.id is not None
    assert subject.name == "英语"
    assert subject.description == "英语科目"

    levels = await Level.filter(subject_id=subject.id)
    assert len(levels) == 3
    assert levels[0].name == "第1级"


@pytest.mark.asyncio
async def test_update_subject(test_db):
    """测试更新科目"""
    subject = await Subject.create(name="物理", code="PHY")
    updated = await SubjectService.update_subject(subject.id, name="新物理", description="新版")

    assert updated.name == "新物理"
    assert updated.description == "新版"


@pytest.mark.asyncio
async def test_delete_subject(test_db):
    """测试删除科目"""
    subject = await Subject.create(name="化学", code="CHEM")
    subject_id = subject.id

    await SubjectService.delete_subject(subject_id)

    result = await Subject.get_or_none(id=subject_id)
    assert result is None


@pytest.mark.asyncio
async def test_create_level(test_db):
    """测试创建等级"""
    subject = await Subject.create(name="生物", code="BIO")
    level = await SubjectService.create_level(subject.id, name="进阶", description="高级难度")

    assert level.id is not None
    assert level.name == "进阶"
    assert level.subject_id == subject.id


@pytest.mark.asyncio
async def test_update_level(test_db):
    """测试更新等级"""
    subject = await Subject.create(name="历史", code="HIS")
    level = await Level.create(name="初级", description="初级难度", subject=subject)

    updated = await SubjectService.update_level(level.id, name="中级", description="中级难度")

    assert updated.name == "中级"
    assert updated.description == "中级难度"


@pytest.mark.asyncio
async def test_delete_level(test_db):
    """测试删除等级"""
    subject = await Subject.create(name="地理", code="GEO")
    level = await Level.create(name="基础", description="基础", subject=subject)
    level_id = level.id

    await SubjectService.delete_level(level_id)

    result = await Level.get_or_none(id=level_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_subjects_with_stats(test_db):
    """测试获取科目统计信息"""
    subject = await Subject.create(name="数学", code="MATH")
    await Level.create(name="第1级", subject=subject)
    await Level.create(name="第2级", subject=subject)
    await KnowledgePoint.create(name="代数", subject=subject, level_id=subject.id)

    result = await SubjectService.get_subjects_with_stats()

    assert len(result) == 1
    assert result[0]["name"] == "数学"
    assert result[0]["level_count"] == 2


# ==================== ExamService Tests ====================

@pytest.mark.asyncio
async def test_get_exam_or_404(test_db):
    """测试获取试卷"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher", email="t@example.com", password_hash="hash", role="teacher")
    exam = await Exam.create(title="期末考试", subject=subject, creator=teacher)

    result = await ExamService.get_exam_or_404(exam.id)
    assert result.id == exam.id


@pytest.mark.asyncio
async def test_create_exam(test_db):
    """测试创建试卷"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher2", email="t2@example.com", password_hash="hash", role="teacher")

    exam = await ExamService.create_exam(
        title="期中考试",
        subject_id=subject.id,
        creator=teacher,
        duration_minutes=90,
        total_points=100,
        pass_score=60,
        is_published=True
    )

    assert exam.id is not None
    assert exam.title == "期中考试"
    assert exam.duration_minutes == 90


@pytest.mark.asyncio
async def test_create_exam_empty_title(test_db):
    """测试空标题创建试卷"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher3", email="t3@example.com", password_hash="hash", role="teacher")

    with pytest.raises(ValidationException):
        await ExamService.create_exam(
            title="",
            subject_id=subject.id,
            creator=teacher
        )


@pytest.mark.asyncio
async def test_update_exam(test_db):
    """测试更新试卷"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher4", email="t4@example.com", password_hash="hash", role="teacher")
    exam = await Exam.create(title="原标题", subject=subject, creator=teacher)

    updated = await ExamService.update_exam(exam.id, title="新标题", duration_minutes=120)

    assert updated.title == "新标题"
    assert updated.duration_minutes == 120


@pytest.mark.asyncio
async def test_delete_exam(test_db):
    """测试删除试卷"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher5", email="t5@example.com", password_hash="hash", role="teacher")
    exam = await Exam.create(title="待删除", subject=subject, creator=teacher)
    exam_id = exam.id

    await ExamService.delete_exam(exam_id)

    result = await Exam.get_or_none(id=exam_id)
    assert result is None


@pytest.mark.asyncio
async def test_batch_delete_exam(test_db):
    """测试批量删除试卷"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher6", email="t6@example.com", password_hash="hash", role="teacher")

    exam1 = await Exam.create(title="考试1", subject=subject, creator=teacher)
    exam2 = await Exam.create(title="考试2", subject=subject, creator=teacher)

    deleted = await ExamService.batch_delete([exam1.id, exam2.id])
    assert deleted == 2


@pytest.mark.asyncio
async def test_batch_publish_exam(test_db):
    """测试批量发布试卷"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher7", email="t7@example.com", password_hash="hash", role="teacher")

    exam1 = await Exam.create(title="考试1", subject=subject, creator=teacher, is_published=False)
    exam2 = await Exam.create(title="考试2", subject=subject, creator=teacher, is_published=False)

    count = await ExamService.batch_publish([exam1.id, exam2.id], is_published=True)
    assert count == 2

    # 验证
    e1 = await Exam.get(id=exam1.id)
    e2 = await Exam.get(id=exam2.id)
    assert e1.is_published is True
    assert e2.is_published is True


@pytest.mark.asyncio
async def test_create_questions_from_data(test_db):
    """测试从数据创建题目"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher8", email="t8@example.com", password_hash="hash", role="teacher")
    exam = await Exam.create(title="测试试卷", subject=subject, creator=teacher)

    questions_data = [
        {
            "type": "single_choice",
            "content": "1+1=?",
            "options": [{"id": "A", "text": "1"}, {"id": "B", "text": "2"}],
            "correct_answer": "B",
            "points": 10
        },
        {
            "type": "single_choice",
            "content": "2+2=?",
            "options": [{"id": "A", "text": "3"}, {"id": "B", "text": "4"}],
            "correct_answer": "B",
            "points": 10
        }
    ]

    created, failed = await ExamService.create_questions_from_data(exam, questions_data)

    assert created == 2
    assert failed == 0

    # 验证题目已创建
    db_questions = await Question.filter(exam_id=exam.id)
    assert len(db_questions) == 2


# ==================== QuestionService Tests ====================

@pytest.mark.asyncio
async def test_get_question_or_404(test_db):
    """测试获取题目"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher9", email="t9@example.com", password_hash="hash", role="teacher")
    exam = await Exam.create(title="测试", subject=subject, creator=teacher)
    question = await Question.create(
        exam=exam,
        type="single_choice",
        content="test",
        correct_answer="A",
        points=10
    )

    result = await QuestionService.get_question_or_404(question.id)
    assert result.id == question.id


@pytest.mark.asyncio
async def test_get_questions_by_exam(test_db):
    """测试获取试卷下的所有题目"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher10", email="t10@example.com", password_hash="hash", role="teacher")
    exam = await Exam.create(title="测试", subject=subject, creator=teacher)

    await Question.create(exam=exam, type="single_choice", content="Q1", correct_answer="A", points=10, order_num=1)
    await Question.create(exam=exam, type="single_choice", content="Q2", correct_answer="B", points=10, order_num=2)

    questions = await QuestionService.get_questions_by_exam(exam.id)
    assert len(questions) == 2


@pytest.mark.asyncio
async def test_create_question(test_db):
    """测试创建题目"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher11", email="t11@example.com", password_hash="hash", role="teacher")
    exam = await Exam.create(title="测试", subject=subject, creator=teacher)

    question = await QuestionService.create_question(
        exam_id=exam.id,
        type="single_choice",
        content="3+3=?",
        correct_answer="C",
        points=10,
        options={"A": "5", "B": "6", "C": "7", "D": "8"}
    )

    assert question.id is not None
    assert question.content == "3+3=?"
    assert question.order_num == 1


@pytest.mark.asyncio
async def test_create_question_exam_not_found(test_db):
    """测试为不存在的试卷创建题目"""
    with pytest.raises(NotFoundException):
        await QuestionService.create_question(exam_id=9999, content="test")


@pytest.mark.asyncio
async def test_update_question(test_db):
    """测试更新题目"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher12", email="t12@example.com", password_hash="hash", role="teacher")
    exam = await Exam.create(title="测试", subject=subject, creator=teacher)
    question = await Question.create(
        exam=exam,
        type="single_choice",
        content="原始内容",
        correct_answer="A",
        points=5
    )

    updated = await QuestionService.update_question(
        question.id,
        content="新内容",
        points=10
    )

    assert updated.content == "新内容"
    assert updated.points == 10


@pytest.mark.asyncio
async def test_delete_question(test_db):
    """测试删除题目"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher13", email="t13@example.com", password_hash="hash", role="teacher")
    exam = await Exam.create(title="测试", subject=subject, creator=teacher)
    question = await Question.create(exam=exam, type="single_choice", content="待删除", correct_answer="A", points=10)
    q_id = question.id

    await QuestionService.delete_question(q_id)

    result = await Question.get_or_none(id=q_id)
    assert result is None


@pytest.mark.asyncio
async def test_batch_delete_questions(test_db):
    """测试批量删除题目"""
    subject = await Subject.create(name="数学", code="MATH")
    teacher = await User.create(username="teacher14", email="t14@example.com", password_hash="hash", role="teacher")
    exam = await Exam.create(title="测试", subject=subject, creator=teacher)

    q1 = await Question.create(exam=exam, type="single_choice", content="Q1", correct_answer="A", points=10)
    q2 = await Question.create(exam=exam, type="single_choice", content="Q2", correct_answer="B", points=10)

    deleted = await QuestionService.batch_delete([q1.id, q2.id])
    assert deleted == 2

    remaining = await Question.filter(id__in=[q1.id, q2.id])
    assert len(remaining) == 0
