"""试卷模型"""

from typing import List, Optional
from datetime import datetime
from app.extensions import db
from .base import BaseModel


class Exam(BaseModel):
    """
    试卷模型
    
    表示一套完整的试卷，包含多个题目
    """
    
    __tablename__ = 'exams'
    
    # 字段定义
    title = db.Column(
        db.String(200),
        nullable=False,
        doc='试卷标题'
    )
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey('subjects.id', ondelete='SET NULL'),
        nullable=True,
        doc='科目ID'
    )
    level_id = db.Column(
        db.Integer,
        db.ForeignKey('levels.id', ondelete='SET NULL'),
        nullable=True,
        doc='等级ID'
    )
    total_points = db.Column(
        db.Integer,
        default=100,
        nullable=False,
        doc='总分'
    )
    question_count = db.Column(
        db.Integer,
        default=0,
        nullable=False,
        doc='题目数量'
    )
    has_images = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        doc='是否包含图片'
    )
    file_path = db.Column(
        db.String(500),
        nullable=True,
        doc='原始文件路径'
    )
    is_temporary = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        index=True,
        doc='是否为临时练习试卷（真题试卷为False，临时试卷为True）'
    )
    description = db.Column(
        db.Text,
        nullable=True,
        doc='考试描述'
    )
    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        doc='是否启用'
    )
    duration_minutes = db.Column(
        db.Integer,
        nullable=True,
        doc='考试时长（分钟）'
    )
    start_time = db.Column(
        db.DateTime,
        nullable=True,
        doc='开始时间'
    )
    end_time = db.Column(
        db.DateTime,
        nullable=True,
        doc='结束时间'
    )
    max_attempts = db.Column(
        db.Integer,
        default=1,
        nullable=True,
        doc='最大尝试次数（null或0表示不限次数）'
    )
    pass_score = db.Column(
        db.Float,
        default=60.0,
        nullable=False,
        doc='及格分数'
    )
    
    # 关系定义
    subject = db.relationship(
        'Subject',
        back_populates='exams',
        lazy='joined',
        doc='关联的科目'
    )
    level = db.relationship(
        'Level',
        back_populates='exams',
        lazy='joined',
        doc='关联的等级'
    )
    questions = db.relationship(
        'Question',
        back_populates='exam',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Question.order_index',
        doc='关联的题目（旧的一对多关系）'
    )
    # 新增：通过关联表获取的题目列表（用于临时试卷引用题库题目）
    exam_questions = db.relationship(
        'ExamQuestion',
        back_populates='exam',
        cascade='all, delete-orphan',
        doc='考试-题目关联记录'
    )
    submissions = db.relationship(
        'Submission',
        back_populates='exam',
        lazy='dynamic',
        cascade='all, delete-orphan',
        doc='关联的答题提交'
    )
    
    def __init__(
        self,
        title: str,
        subject_id: Optional[int] = None,
        level_id: Optional[int] = None,
        total_points: int = 100,
        file_path: Optional[str] = None,
        is_temporary: bool = False,
        description: Optional[str] = None,
        is_active: bool = True,
        duration_minutes: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_attempts: int = 1,
        pass_score: float = 60.0
    ):
        """
        初始化试卷

        Args:
            title: 试卷标题
            subject_id: 科目ID（可选）
            level_id: 等级ID（可选）
            total_points: 总分，默认100
            file_path: 原始文件路径（可选）
            is_temporary: 是否为临时试卷，默认False
            description: 考试描述（可选）
            is_active: 是否启用，默认True
            duration_minutes: 考试时长（分钟）（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            max_attempts: 最大尝试次数，默认1
            pass_score: 及格分数，默认60.0
        """
        self.title = title
        self.subject_id = subject_id
        self.level_id = level_id
        self.total_points = total_points
        self.file_path = file_path
        self.is_temporary = is_temporary
        self.description = description
        self.is_active = is_active
        self.duration_minutes = duration_minutes
        self.start_time = start_time
        self.end_time = end_time
        self.max_attempts = max_attempts
        self.pass_score = pass_score
        self.question_count = 0
        self.has_images = False
    
    @classmethod
    def get_by_title(cls, title: str) -> Optional['Exam']:
        """
        根据标题获取试卷
        
        Args:
            title: 试卷标题
            
        Returns:
            试卷实例，如果不存在则返回None
        """
        return cls.query.filter_by(title=title).first()
    
    @classmethod
    def search(
        cls,
        keyword: Optional[str] = None,
        subject_id: Optional[int] = None,
        level_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List['Exam']:
        """
        搜索试卷
        
        Args:
            keyword: 关键词（在标题中搜索）
            subject_id: 科目ID筛选
            level_id: 等级ID筛选
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            试卷列表
        """
        query = cls.query
        
        if keyword:
            query = query.filter(cls.title.ilike(f'%{keyword}%'))
        
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        
        if level_id:
            query = query.filter_by(level_id=level_id)
        
        return query.order_by(cls.created_at.desc()).offset(offset).limit(limit).all()
    
    def update_statistics(self) -> None:
        """更新试卷统计信息（题目数量、是否有图片）"""
        from datetime import datetime, timezone
        self.question_count = self.questions.count()
        self.has_images = any(question.has_image for question in self.questions.all())
        self.updated_at = datetime.now(timezone.utc)
        db.session.commit()

    def get_all_questions(self):
        """获取试卷的所有题目

        包括：
        1. 直接关联的题目（旧方式，exam_id不为None）
        2. 通过关联表关联的题目（新方式，用于临时试卷）

        Returns:
            题目列表，按order_index排序
        """
        from app.models.exam_question import ExamQuestion

        # 如果是通过关联表关联的题目（临时试卷）
        exam_questions = ExamQuestion.query.filter_by(exam_id=self.id).order_by(ExamQuestion.order_index).all()
        if exam_questions:
            return [eq.question for eq in exam_questions]

        # 否则使用旧的一对多关系
        return self.questions.all()
    
    def get_subject_name(self) -> Optional[str]:
        """
        获取科目名称
        
        Returns:
            科目名称，如果没有关联科目则返回None
        """
        return self.subject.name if self.subject else None
    
    def get_level_name(self) -> Optional[str]:
        """
        获取等级名称
        
        Returns:
            等级名称，如果没有关联等级则返回None
        """
        return self.level.name if self.level else None
    
    def get_average_score(self) -> Optional[float]:
        """
        获取平均分
        
        Returns:
            平均分，如果没有提交记录则返回None
        """
        submissions = self.submissions.filter_by(is_completed=True).all()
        if not submissions:
            return None
        
        total = sum(sub.total_score for sub in submissions)
        return total / len(submissions)
    
    def to_dict(self, include_questions: bool = False) -> dict:
        """
        转换为字典，可包含关联的题目

        Args:
            include_questions: 是否包含题目信息

        Returns:
            包含试卷信息的字典
        """
        data = super().to_dict()

        # 添加关联对象信息（前端需要完整的subject和level对象）
        if self.subject:
            data['subject'] = self.subject.to_dict()
        if self.level:
            data['level'] = self.level.to_dict()

        # 添加名称字段（保留兼容性）
        data['subject_name'] = self.get_subject_name()
        data['level_name'] = self.get_level_name()

        if include_questions:
            data['questions'] = [q.to_dict() for q in self.get_all_questions()]

        # 添加统计信息
        data['average_score'] = self.get_average_score()
        data['submission_count'] = self.submissions.count()

        return data
    
    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f'<Exam id={self.id} title="{self.title}">'