"""文件上传路由"""

import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.parsers.ai_document_parser import AIDocumentParser
from app.services import ExamService, QuestionService
from app.extensions import db


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
    """解析上传的文档（使用AI）"""
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
            return jsonify({
                'success': False,
                'message': f'不支持的文件格式。支持的格式: .docx, .doc, .txt'
            }), 400

        # 保存文件
        file_path, original_filename = save_uploaded_file(file)

        try:
            # 创建进度回调函数，将进度信息存储到全局变量供轮询接口使用
            import threading
            progress_data = {'percent': 0, 'message': '准备解析...'}
            parse_id = str(uuid.uuid4())

            # 存储进度信息到内存（实际项目中可以使用Redis）
            if not hasattr(parse_document, 'progress_store'):
                parse_document.progress_store = {}
            parse_document.progress_store[parse_id] = progress_data

            def progress_callback(percent, message):
                """进度回调函数"""
                progress_data['percent'] = percent
                progress_data['message'] = message
                print(f"[进度 {percent}%] {message}")

            # 使用AI解析器解析文档
            ai_parser = AIDocumentParser(use_ai=True, progress_callback=progress_callback)
            parsed_data = ai_parser.parse_document(file_path)

            # 返回解析结果（包含parse_id用于获取日志）
            return jsonify({
                'success': True,
                'data': {
                    'question_count': parsed_data.get('question_count', 0),
                    'questions_preview': parsed_data.get('questions', [])[:5],  # 预览前5个问题
                    'uploaded_file': original_filename,
                    'parse_method': parsed_data.get('parse_method', 'ai'),
                    'parse_log': parsed_data.get('parse_log', ''),
                    'parse_id': parse_id
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


@upload_bp.route('/upload/progress/<parse_id>', methods=['GET'])
def get_parse_progress(parse_id):
    """获取解析进度（实时进度查询）"""
    try:
        if not hasattr(parse_document, 'progress_store'):
            parse_document.progress_store = {}

        progress_data = parse_document.progress_store.get(parse_id)

        if not progress_data:
            return jsonify({
                'success': False,
                'message': '解析任务不存在或已过期'
            }), 404

        return jsonify({
            'success': True,
            'data': {
                'percent': progress_data.get('percent', 0),
                'message': progress_data.get('message', '')
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取进度失败: {str(e)}'
        }), 500


@upload_bp.route('/upload/create_exam', methods=['POST'])
def create_exam_from_document():
    """从文档创建考试（使用AI解析）"""
    try:
        # 解析请求数据
        data = request.form
        if not data:
            return jsonify({
                'success': False,
                'message': '缺少表单数据'
            }), 400

        # 检查必填字段
        required_fields = ['subject_id', 'level_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'缺少必填字段: {", ".join(missing_fields)}'
            }), 400

        # 如果没有提供标题，自动生成
        title = data.get('title', '').strip()
        if not title:
            # 从文件名生成标题（去掉扩展名）
            file = request.files['file']
            if file.filename:
                title = file.filename.rsplit('.', 1)[0]
            else:
                title = '未命名试卷'

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
            return jsonify({
                'success': False,
                'message': f'不支持的文件格式。支持的格式: .docx, .doc, .txt'
            }), 400

        # 保存文件
        file_path, original_filename = save_uploaded_file(file)

        try:
            # 使用AI解析器解析文档
            ai_parser = AIDocumentParser(use_ai=True)
            parse_result = ai_parser.parse_document(file_path)

            # 从表单数据获取用户输入的时长和分值
            duration_minutes_input = data.get('duration_minutes')
            total_points_input = data.get('total_points')

            # 构建试卷数据
            exam_data = {
                'title': title,
                'subject_id': int(data['subject_id']),
                'level_id': int(data['level_id']),
                'description': f"从文件 '{original_filename}' 导入",
                'duration_minutes': int(duration_minutes_input) if duration_minutes_input else 60,
                'total_points': int(total_points_input) if total_points_input else 100,
                'questions': parse_result.get('questions', []),
                'parse_method': parse_result.get('parse_method', 'ai'),
                'question_count': len(parse_result.get('questions', []))
            }

            # 创建试卷
            db = current_app.extensions['sqlalchemy']
            exam_service = ExamService(db)

            exam = exam_service.create_exam(
                title=exam_data['title'],
                subject_id=exam_data['subject_id'],
                level_id=exam_data['level_id'],
                description=exam_data.get('description', ''),
                duration_minutes=exam_data.get('duration_minutes'),
                start_time=None,
                end_time=None,
                is_active=data.get('is_active', 'true').lower() == 'true',
                max_attempts=1,
                pass_score=60.0,
                total_points=exam_data.get('total_points')
            )

            # 创建问题
            question_service = QuestionService(db)
            created_questions = []
            failed_questions = []

            print(f'开始创建题目，共 {len(exam_data.get("questions", []))} 道题目')
            for i, q_data in enumerate(exam_data['questions']):
                try:
                    # 将选项列表转换为选项字典格式
                    options_list = q_data.get('options', [])
                    options_dict = {}
                    if options_list:
                        # 保留选项中的has_image信息
                        formatted_options = []
                        for opt in options_list:
                            formatted_options.append({
                                'id': opt.get('id', chr(65 + len(formatted_options))),
                                'text': opt.get('text', ''),
                                'has_image': opt.get('has_image', False)
                            })
                        options_dict = {'choices': [opt.get('text', '') for opt in formatted_options]}

                    # 处理图片标识
                    has_image = q_data.get('content_has_image', False)

                    # 处理考点 - 暂时存储在metadata中，后续可关联KnowledgePoint
                    knowledge_point = q_data.get('knowledge_point', '')
                    metadata = {}
                    if knowledge_point:
                        metadata['knowledge_point_text'] = knowledge_point

                    print(f'创建第 {i+1} 道题目，exam_id={exam.id}, has_image={has_image}, knowledge_point={knowledge_point}')
                    question = question_service.create_question(
                        exam_id=exam.id,
                        content=q_data.get('content', f'问题 {i+1}'),
                        question_type=q_data.get('type', 'single_choice'),
                        score=float(q_data.get('points', 10)),
                        options=options_dict,
                        correct_answer=q_data.get('correct_answer', ''),
                        explanation=q_data.get('explanation', ''),
                        order_index=q_data.get('order_index', i + 1)
                    )

                    # 额外设置has_image和metadata
                    question.has_image = has_image
                    if metadata:
                        question.question_metadata = metadata
                    db.session.commit()

                    print(f'题目创建成功，ID={question.id}, has_image={question.has_image}')
                    created_questions.append(question.id)
                except Exception as e:
                    import traceback
                    print(f'创建题目失败: {e}')
                    traceback.print_exc()
                    failed_questions.append({
                        'index': i,
                        'content': q_data.get('content', '')[:100],
                        'error': str(e)
                    })

            # 刷新试卷对象并更新统计信息（题目数量）
            db.session.refresh(exam)
            print(f'刷新后试卷题目数（before update_statistics）: {exam.questions.count()}')

            try:
                exam.update_statistics()
                print(f'更新后试卷题目数（after update_statistics）: {exam.question_count}')
            except Exception as e:
                import traceback
                print(f'更新试卷统计失败: {e}')
                traceback.print_exc()
                db.session.rollback()

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
                    'source_file': original_filename,
                    'parse_method': exam_data.get('parse_method', 'ai'),
                    'parse_log': parse_result.get('parse_log', '')
                },
                'message': f'试卷创建成功，共导入 {len(created_questions)} 道题目'
            })

        except Exception as e:
            # 删除临时文件
            try:
                os.remove(file_path)
            except:
                pass

            return jsonify({
                'success': False,
                'message': f'创建试卷失败: {str(e)}'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理请求失败: {str(e)}'
        }), 500


@upload_bp.route('/upload/supported_formats', methods=['GET'])
def get_supported_formats():
    """获取支持的文件格式"""
    formats = {
        '.docx': 'Word文档（支持AI智能解析）',
        '.doc': 'Word文档（旧版）',
        '.txt': '纯文本文件',
        '.text': '纯文本文件'
    }

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