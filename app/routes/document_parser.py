"""文档解析路由"""

from flask import Blueprint, request, jsonify, send_from_directory, current_app
from werkzeug.utils import secure_filename
import os

document_parser_bp = Blueprint('document_parser', __name__)


# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'docx', 'pdf'}


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@document_parser_bp.route('/parse', methods=['POST'])
def parse_document():
    """解析文档并提取试题

    POST /api/document-parser/parse

    请求体格式（multipart/form-data）:
        file: 文件
        subject_id: 科目ID（可选）
        level_id: 等级ID（可选）
    """
    try:
        from app.services.document_parser import DocumentParserService
        from app.extensions import db

        # 检查是否有文件
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
                'message': '未选择文件'
            }), 400

        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': '不支持的文件类型，仅支持 .docx 和 .pdf'
            }), 400

        # 保存文件
        filename = secure_filename(file.filename)
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        # 获取文件类型
        file_type = filename.rsplit('.', 1)[1].lower()

        # 解析文档
        parser_service = DocumentParserService(db)
        result = parser_service.parse_document(file_path, file_type)

        # 验证试题
        if result['success'] and result['questions']:
            from app.services.document_parser import DocumentParserService
            parser_service = DocumentParserService(db)
            validated_questions = parser_service.validate_questions(result['questions'])
            result['questions'] = validated_questions
            result['question_count'] = len(validated_questions)

        # 删除临时文件
        try:
            os.remove(file_path)
        except:
            pass

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'文档解析失败: {str(e)}'
        }), 500


@document_parser_bp.route('/parse/text', methods=['POST'])
def parse_text():
    """从文本中提取试题

    POST /api/document-parser/parse/text

    请求体:
        {
            "text": "文本内容"
        }
    """
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'message': '缺少文本内容'
            }), 400

        text = data['text']

        # 使用AI提取试题
        from app.services.ai_service import get_ai_service
        ai_service = get_ai_service()

        # 更新最后使用时间
        from app.models.ai_config import AIConfig
        config = AIConfig.get_active_provider()
        if config:
            config.update_last_used()

        # 提取试题
        questions = ai_service.extract_questions_from_text(text)

        # 验证试题
        from app.services.document_parser import DocumentParserService
        from app.extensions import db
        parser_service = DocumentParserService(db)
        validated_questions = parser_service.validate_questions(questions)

        return jsonify({
            'success': True,
            'questions': validated_questions,
            'question_count': len(validated_questions)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'文本解析失败: {str(e)}'
        }), 500


@document_parser_bp.route('/summarize', methods=['POST'])
def summarize_document():
    """生成文档摘要

    POST /api/document-parser/summarize

    请求体:
        {
            "text": "文本内容"
        }
    """
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'message': '缺少文本内容'
            }), 400

        text = data['text']

        # 使用AI生成摘要
        from app.services.ai_service import get_ai_service
        ai_service = get_ai_service()

        # 更新最后使用时间
        from app.models.ai_config import AIConfig
        config = AIConfig.get_active_provider()
        if config:
            config.update_last_used()

        # 生成摘要
        summary = ai_service.summarize_document(text)

        return jsonify({
            'success': True,
            'summary': summary
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'摘要生成失败: {str(e)}'
        }), 500
