# 图片提取与存储功能更新

## 概述

本次更新实现了从Word文档中提取图片并保存到文件系统的功能，支持题目图片和选项图片的存储与显示。

## 主要改动

### 1. AI文档解析器 (`app/parsers/ai_document_parser.py`)

#### 新增功能
- **图片提取功能**: `_extract_and_save_image()`
  - 从Word文档的drawing元素中提取图片数据
  - 保存图片到指定的上传目录
  - 自动生成唯一的文件名（UUID + 索引）
  - 支持多种图片格式（PNG, JPEG）

- **改进的图片信息收集**:
  - `_extract_text_and_images_from_docx()` 现在提取并保存图片
  - 图片信息包含文件路径，不仅是标记
  - 区分题目图片和选项图片

- **图片与题目关联**:
  - `_update_question_image_flags()` 更新以支持图片路径
  - 新增 `_extract_option_id()` 从文本中提取选项ID（A、B、C、D）

#### 数据结构变化
```python
# image_info 现在包含:
{
    'location': 'paragraph_123',
    'question_number': 1,
    'image_type': 'question_image' or 'option_image',
    'text_context': '上下文文本',
    'image_path': 'uploads/images/image_xxx_0001.png'  # 新增
}

# question 数据现在包含:
{
    'content_has_image': True,
    'image_path': 'uploads/images/image_xxx_0001.png',  # 新增
    'options': [
        {
            'id': 'A',
            'text': '选项内容',
            'has_image': True,
            'image_path': 'uploads/images/image_xxx_0002.png'  # 新增
        }
    ]
}
```

### 2. 上传路由 (`app/routes/upload.py`)

#### 新增功能
- **图片文件服务路由**: `/uploads/<path:filename>`
  - 提供上传的图片文件访问
  - 包含安全检查，防止目录遍历攻击
  - 支持相对路径和文件名

#### 修改内容
- AIDocumentParser 初始化时传入 `upload_folder` 参数
- 图片保存到 `uploads/images/` 目录
- 题目创建时保存图片路径到 `image_data` 字段
- 选项图片信息保存到 `question_metadata['options_images']`

### 3. 模板更新

#### 考试页面 (`templates/exam/take_exam.html`)
- 题目图片显示支持文件路径
- 选项图片显示（单选题和多选题）
- 使用 `url_for('upload.uploaded_file', filename=...)` 获取图片

#### 结果页面 (`templates/submission/result.html`)
- 题目图片显示支持文件路径
- 选项图片显示（从 metadata 中读取）
- 显示选项的正确答案标识

### 4. 数据库模型 (`app/models/question.py`)
- `image_data` 字段：存储图片文件路径（相对路径）
  - 格式1: `data:image/png;base64,...` (base64编码)
  - 格式2: `uploads/images/image_xxx.png` (文件路径)
- `question_metadata` 字段：存储选项图片信息
  ```python
  {
    'options_images': {
      'A': {'has_image': True, 'image_path': 'uploads/images/...'},
      'B': {'has_image': True, 'image_path': 'uploads/images/...'}
    }
  }
  ```

## 使用方式

### 解析Word文档并提取图片

```python
from app.parsers.ai_document_parser import AIDocumentParser

parser = AIDocumentParser(use_ai=True, upload_folder='uploads/images')
result = parser.parse_document('exam.docx')

# result['questions'] 包含图片路径信息
for question in result['questions']:
    if question['content_has_image']:
        print(f"题目图片: {question['image_path']}")

    for option in question.get('options', []):
        if option.get('has_image'):
            print(f"选项图片 {option['id']}: {option['image_path']}")
```

### 创建考试时保存图片

```python
question = QuestionService(db).create_question(
    exam_id=exam.id,
    content="题目内容",
    question_type="single_choice",
    ...
)

# 设置题目图片
question.has_image = True
question.image_data = "uploads/images/image_xxx.png"

# 设置选项图片（通过metadata）
question.question_metadata = {
    'options_images': {
        'A': {'has_image': True, 'image_path': 'uploads/images/image_xxx.png'}
    }
}
```

### 在模板中显示图片

```jinja2
{# 题目图片 #}
{% if question.has_image and question.image_data %}
  {% if question.image_data.startswith('data:') %}
    <img src="{{ question.image_data }}">
  {% else %}
    <img src="{{ url_for('upload.uploaded_file', filename=question.image_data) }}">
  {% endif %}
{% endif %}

{# 选项图片 #}
{% for option in question.options %}
  <label>
    <span>{{ option.id }}.</span> {{ option.text }}
    {% if option.has_image and option.image_path %}
      <img src="{{ url_for('upload.uploaded_file', filename=option.image_path) }}">
    {% endif %}
  </label>
{% endfor %}
```

## 测试

运行测试脚本验证图片提取功能：

```bash
python test_image_extraction.py
```

该脚本会：
1. 查找测试Word文档
2. 提取文档中的图片
3. 验证图片与题目的关联
4. 检查图片文件是否正确保存

## 注意事项

1. **图片目录**: 图片默认保存到 `uploads/images/` 目录
2. **文件名格式**: `image_{uuid}_{index:04d}.{ext}`
3. **路径存储**: 数据库存储相对路径，便于迁移
4. **安全检查**: 文件服务路由包含目录遍历防护
5. **向后兼容**: 支持旧的 base64 格式和新的文件路径格式

## 后续改进

1. 支持更多图片格式（GIF, WebP等）
2. 图片压缩和优化
3. 图片CDN集成
4. 批量图片管理功能
