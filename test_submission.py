#!/usr/bin/env python
"""测试提交页面"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Exam, Submission
from app.services import SubmissionService
from app.extensions import db

app = create_app('development')
with app.app_context():
    # 找考试1
    exam = Exam.query.get(1)
    print(f'考试1: {exam.title}')

    # 创建一个测试提交记录
    submission_service = SubmissionService(db)
    submission = submission_service.create_submission(
        exam_id=1,
        user_id=1
    )
    print(f'创建提交记录: ID={submission.id}')

    # 现在访问该页面
    with app.test_client() as client:
        try:
            response = client.get(f'/exam/{submission.id}')
            print(f'Status: {response.status_code}')
            if response.status_code == 500:
                print('500错误！')
                error_text = response.data.decode()
                if 'unsupported operand' in error_text:
                    print(error_text[:1500])
        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()
