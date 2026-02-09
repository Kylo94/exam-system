"""文件上传路由"""

import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.parsers import ParserFactory
from app.services import ExamService, QuestionService


# 创建蓝图
upload_bp = Blueprint('upload', __name__)


def allowed_file(filename):
    """检查文件扩展名是否允许
    
    Args:
        filename: 文件名
        
    Returns:
        是否允许上传
    """
    allowed_extensions = {'.docx', '.doc', '.txt', '.text'}
    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions


def save_uploaded_file(file):
    """保存上传的文件
    
    Args:
        file: 上传的文件对象
        
    Returns:
        保存的文件路径
    """
    # 生成唯一文件名
    original_filename = secure_filename(file.filename)
    ext = Path(original_filename).suffix.lower()
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    
    # 确保上传目录存在
    upload_dir = Path(current_app.config.get('UPLOAD_FOLDER', 'uploads'))
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存文件
    file_path = upload_dir / unique_filename
    file.save(str(file_path))
    
    return str(file_path), original_filename


@upload_bp.route('/upload/parse', methods=['POST'])
def parse_document():
    """解析上传的文档"""
    try:
        # 检查文件是否存在
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有上传文件'
            }), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400
        
        # 检查文件类型
        if not allowed_file(file.filename):
            supported = ', '.join(ParserFactory.get_supported_formats().keys())
            return jsonify({
                'success': False,
                'message': f'不支持的文件格式。支持的格式: {supported}'
            }), 400
        
        # 保存文件
        file_path, original_filename = save_uploaded_file(file)
        
        try:
            # 解析文档
            parsed_data = ParserFactory.parse_file(file_path)
            
            # 返回解析结果
            return jsonify({
                'success': True,
                'data': {
                    'file_info': parsed_data['file_info'],
                    'metadata': parsed_data['metadata'],
                    'question_count': len(parsed_data.get('questions', [])),
                    'questions_preview': parsed_data.get('questions', [])[:5],  # 预览前5个问题
                    'uploaded_file': original_filename,
                    'saved_path': file_path
                },
                'message': '文档解析成功'
            })
            
        except Exception as e:
            # 删除临时文件
            try:
                os.remove(file_path)
            except:
                pass
            
            return jsonify({
                'success': False,
                'message': f'文档解析失败: {str(e)}'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'上传失败: {str(e)}'
        }), 500


@upload_bp.route('/upload/create_exam', methods=['POST'])
def create_exam_from_document():
    """从文档创建考试"""
    try:
        # 解析请求数据
        data = request.form
        if not data:
            return jsonify({
                'success': False,
                'message': '缺少表单数据'
            }), 400
        
        # 检查必填字段
        required_fields = ['title', 'subject_id', 'level_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'缺少必填字段: {", ".join(missing_fields)}'
            }), 400
        
        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有上传文件'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400
        
        if not allowed_file(file.filename):
            supported = ', '.join(ParserFactory.get_supported_formats().keys())
            return jsonify({
                'success': False,
                'message': f'不支持的文件格式。支持的格式: {supported}'
            }), 400
        
        # 保存文件
        file_path, original_filename = save_uploaded_file(file)
        
        try:
            # 解析文档并创建考试数据
            exam_data = ParserFactory.parse_to_exam(
                file_path=file_path,
                exam_title=data['title'],
                subject_id=int(data['subject_id']),
                level_id=int(data['level_id'])
            )
            
            # 创建考试
            db = current_app.extensions['sqlalchemy']
            exam_service = ExamService(db)
            
            exam = exam_service.create_exam(
                title=exam_data['title'],
                subject_id=exam_data['subject_id'],
                level_id=exam_data['level_id'],
                description=exam_data.get('description', ''),
                duration_minutes=exam_data.get('duration_minutes', 60),
                start_time=data.get('start_time'),
                end_time=data.get('end_time'),
                is_active=data.get('is_active', 'true').lower() == 'true',
                max_attempts=int(data.get('max_attempts', 1)),
                pass_score=float(data.get('pass_score', 60.0))
            )
            
            # 创建问题
            question_service = QuestionService(db)
            created_questions = []
            failed_questions = []
            
            for i, q_data in enumerate(exam_data['questions']):
                try:
                    question = question_service.create_question(
                        exam_id=exam.id,
                        content=q_data.get('content', f'问题 {i+1}'),
                        question_type=q_data.get('type', 'single_choice'),
                        score=q_data.get('score', 1.0),
                        options=q_data.get('options'),
                        correct_answer=q_data.get('correct_answer'),
                        explanation=q_data.get('explanation', ''),
                        order_index=q_data.get('order_index', i)
                    )
                    created_questions.append(question.id)
                except Exception as e:
                    failed_questions.append({
                        'index': i,
                        'error': str(e)
                    })
            
            # 删除临时文件
            try:
                os.remove(file_path)
            except:
                pass
            
            return jsonify({
                'success': True,
                'data': {
                    'exam': {
                        'id': exam.id,
                        'title': exam.title,
                        'subject_id': exam.subject_id,
                        'level_id': exam.level_id,
                        'question_count': len(created_questions)
                    },
                    'questions': {
                        'created': len(created_questions),
                        'failed': len(failed_questions),
                        'failed_details': failed_questions
                    },
                    'source_file': original_filename
                },
                'message': f'考试创建成功，共导入 {len(created_questions)} 个问题'
            })
            
        except Exception as e:
            # 删除临时文件
            try:
                os.remove(file_path)
            except:
                pass
            
            return jsonify({
                'success': False,
                'message': f'创建考试失败: {str(e)}'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理请求失败: {str(e)}'
        }), 500


@upload_bp.route('/upload/supported_formats', methods=['GET'])
def get_supported_formats():
    """获取支持的文件格式"""
    formats = ParserFactory.get_supported_formats()
    
    return jsonify({
        'success': True,
        'data': [
            {
                'extension': ext,
                'description': desc,
                'mime_types': get_mime_type(ext)
            }
            for ext, desc in formats.items()
        ]
    })


def get_mime_type(extension):
    """获取文件扩展名对应的MIME类型
    
    Args:
        extension: 文件扩展名
        
    Returns:
        MIME类型列表
    """
    mime_map = {
        '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        '.doc': ['application/msword'],
        '.txt': ['text/plain'],
        '.text': ['text/plain']
    }
    
    return mime_map.get(extension.lower(), ['application/octet-stream'])


@upload_bp.route('/upload/validate', methods=['POST'])
def validate_document():
    """验证文档格式（不保存文件）"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有上传文件'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400
        
        if not allowed_file(file.filename):
            supported = ', '.join(ParserFactory.get_supported_formats().keys())
            return jsonify({
                'success': False,
                'message': f'不支持的文件格式。支持的格式: {supported}'
            }), 400
        
        # 临时保存文件
        temp_dir = Path(current_app.config.get('UPLOAD_FOLDER', 'uploads')) / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_path = temp_dir / f"temp_{uuid.uuid4().hex}{Path(file.filename).suffix}"
        file.save(str(temp_path))
        
        try:
            # 尝试解析
            parser = ParserFactory.get_parser(str(temp_path))
            if not parser:
                raise ValueError("不支持的文件格式")
            
            parsed_data = parser.parse(str(temp_path))
            questions = parsed_data.get('questions', [])
            
            # 验证问题
            valid_questions = []
            invalid_questions = []
            
            for i, q in enumerate(questions):
                if parser.validate_question(q):
                    valid_questions.append({
                        'index': i,
                        'content_preview': q.get('content', '')[:100] + '...' if len(q.get('content', '')) > 100 else q.get('content', ''),
                        'type': q.get('type'),
                        'score': q.get('score')
                    })
                else:
                    invalid_questions.append({
                        'index': i,
                        'content_preview': q.get('content', '')[:100] + '...' if len(q.get('content', '')) > 100 else q.get('content', ''),
                        'type': q.get('type'),
                        'score': q.get('score')
                    })
            
            # 删除临时文件
            try:
                os.remove(str(temp_path))
            except:
                pass
            
            return jsonify({
                'success': True,
                'data': {
                    'file_name': file.filename,
                    'file_size': temp_path.stat().st_size if temp_path.exists() else 0,
                    'question_count': len(questions),
                    'valid_questions': len(valid_questions),
                    'invalid_questions': len(invalid_questions),
                    'valid_questions_preview': valid_questions[:5],
                    'invalid_questions_preview': invalid_questions[:5]
                },
                'message': f'文档验证成功，发现 {len(questions)} 个问题，其中 {len(valid_questions)} 个有效，{len(invalid_questions)} 个无效'
            })
            
        except Exception as e:
            # 删除临时文件
            try:
                os.remove(str(temp_path))
            except:
                pass
            
            return jsonify({
                'success': False,
                'message': f'文档验证失败: {str(e)}'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'验证失败: {str(e)}'
        }), 500