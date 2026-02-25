# AI功能使用说明

## 功能概述

本系统集成了AI功能，支持：
1. **文档智能解析**：从Word/PDF文档中自动提取试题
2. **AI配置管理**：灵活配置多个AI提供商（DeepSeek、OpenAI等）
3. **文档摘要生成**：自动生成文档内容摘要

## 安装依赖

```bash
pip install python-docx PyPDF2 requests
```

或安装所有依赖：

```bash
pip install -r requirements.txt
```

## 快速开始

### 1. 配置AI服务

访问 `/ai-configs` 页面添加AI配置：

**DeepSeek配置示例：**
- 提供商：`deepseek`
- 模型：`deepseek-chat`
- API地址：`https://api.deepseek.com/v1/chat/completions`
- API密钥：从 [DeepSeek控制台](https://platform.deepseek.com/) 获取

**OpenAI配置示例：**
- 提供商：`openai`
- 模型：`gpt-3.5-turbo`
- API地址：`https://api.openai.com/v1/chat/completions`
- API密钥：从 [OpenAI控制台](https://platform.openai.com/) 获取

### 2. 使用文档解析

#### 方式一：通过API解析文档

```bash
curl -X POST http://localhost:5000/api/document-parser/parse \
  -F "file=@test.docx"
```

#### 方式二：通过API解析文本

```bash
curl -X POST http://localhost:5000/api/document-parser/parse/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "题目内容..."
  }'
```

### 3. 在试卷上传中使用

在创建试卷时，选择"文件上传"方式，系统会自动：
1. 解析上传的Word/PDF文档
2. 使用AI提取试题
3. 显示提取的试题供确认

## API接口说明

### AI配置管理

#### 获取所有AI配置
```
GET /api/ai-configs
```

#### 获取激活的AI配置
```
GET /api/ai-configs/active
```

#### 创建AI配置
```
POST /api/ai-configs
Content-Type: application/json

{
  "provider": "deepseek",
  "api_key": "your-api-key",
  "api_url": "https://api.deepseek.com/v1/chat/completions",
  "model": "deepseek-chat",
  "max_tokens": 2000,
  "temperature": 0.7,
  "description": "DeepSeek配置",
  "is_active": true,
  "is_default": false
}
```

#### 测试AI配置
```
POST /api/ai-configs/{id}/test
```

#### 设置默认配置
```
POST /api/ai-configs/{id}/set-default
```

#### 获取支持的提供商
```
GET /api/ai-configs/providers
```

### 文档解析

#### 解析文档文件
```
POST /api/document-parser/parse
Content-Type: multipart/form-data

file: 文件
subject_id: 科目ID（可选）
level_id: 等级ID（可选）
```

#### 解析文本内容
```
POST /api/document-parser/parse/text
Content-Type: application/json

{
  "text": "题目内容..."
}
```

#### 生成文档摘要
```
POST /api/document-parser/summarize
Content-Type: application/json

{
  "text": "文档内容..."
}
```

## 支持的题型

AI可以识别以下题型：
- `single_choice` - 单选题
- `multiple_choice` - 多选题
- `judgment` - 判断题
- `fill_blank` - 填空题
- `subjective` - 简答题

## 扩展其他AI提供商

### 1. 在 `app/services/ai_service.py` 中添加新的服务类

```python
class NewProviderService(AIServiceBase):
    """新的AI提供商服务实现"""

    def __init__(self, config):
        super().__init__(config)

    def chat(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        # 实现具体的聊天接口
        pass
```

### 2. 在 `provider_map` 中注册

```python
provider_map = {
    'deepseek': DeepSeekService,
    'openai': OpenAIService,
    'new_provider': NewProviderService,  # 新增
}
```

### 3. 在 `app/routes/ai_configs.py` 的 `get_supported_providers` 路由中添加提供商信息

```python
providers = [
    # ... 现有提供商 ...
    {
        'id': 'new_provider',
        'name': '新提供商',
        'description': '描述',
        'default_model': 'model-name',
        'default_api_url': 'https://api.example.com/v1/chat/completions'
    }
]
```

## 注意事项

1. **API密钥安全**：AI配置中的API密钥会存储在数据库中，请确保数据库安全
2. **Token使用**：注意控制max_tokens参数，避免超出API配额
3. **文档格式**：建议使用标准格式的Word文档，复杂的排版可能影响识别效果
4. **试题验证**：AI提取的试题需要人工审核确认

## 故障排查

### AI配置测试失败
- 检查API密钥是否正确
- 检查网络连接
- 检查API地址是否正确

### 文档解析失败
- 确认文件类型是否支持（仅支持.docx和.pdf）
- 检查文件是否损坏
- 查看服务器日志获取详细错误信息

### 提取的试题格式错误
- AI提取的试题格式可能不完美，需要人工调整
- 可以通过`/api/document-parser/parse/text`接口手动输入文本提取
