# 解析失败问题诊断与解决方案

## 问题分析

### 可能的失败原因

1. **图片提取失败**
   - Word文档中的图片提取可能因为：
     - XPath命名空间问题
     - 图片关系ID找不到
     - 图片数据为空
     - 文件权限问题
     - 目录不存在

2. **Word文档格式问题**
   - 某些Word文档格式不规范
   - 包含特殊的对象或嵌入内容
   - 表格结构复杂

3. **内存不足**
   - 大文件或大量图片可能导致内存问题

## 已实现的容错机制

### 1. 分层容错

```python
# 在 parse_document 中
try:
    text, image_info = self._extract_text_and_images_from_docx(file_path)
except Exception as e:
    # 图片提取失败，尝试只提取文本
    self._add_log(f"⚠️ 图片提取失败，尝试只提取文本: {str(e)}", 'warning')
    try:
        text = self._extract_text_only(file_path)
        image_info = []
    except Exception as e2:
        raise Exception(f"文档提取失败: {str(e2)}")
```

### 2. 单个图片提取失败不影响整体

```python
try:
    for run in para.runs:
        # 提取图片
        ...
except Exception as e:
    # 单个图片提取失败不影响整体
    self._add_log(f"  ⚠️ 段落{para_idx}图片提取失败: {str(e)}", 'warning')
```

### 3. 可选的图片提取

```python
# 创建解析器时可以禁用图片提取
parser = AIDocumentParser(
    use_ai=True,
    upload_folder='uploads/images',
    extract_images=True  # 设为False可完全跳过图片提取
)
```

## 调试步骤

### 1. 使用诊断脚本

```bash
python diagnose_parser.py
```

这个脚本会：
- 检查文件是否存在
- 分析文档结构
- 检测图片数量
- 显示文本预览

### 2. 使用简化版解析器

```bash
python simple_parser_test.py
```

这个脚本：
- 不提取图片
- 只专注于文本解析
- 快速验证基本功能

### 3. 查看日志

解析过程中的日志会显示：
- 每个步骤的进度
- 检测到的题目数量
- 图片提取结果
- 任何警告或错误

## 常见问题和解决方案

### 问题1: "找不到图片关系"

**原因**: XPath命名空间问题或图片关系ID无效

**解决方案**:
- 已添加多种XPath尝试方式
- 添加了不带命名空间的属性查找
- 单个图片失败不影响整体

### 问题2: "文档提取失败"

**原因**: Word文档格式不标准或损坏

**解决方案**:
- 尝试在Word中打开并另存为.docx
- 检查文件是否损坏
- 使用简化版解析器测试

### 问题3: "图片数据为空"

**原因**: 图片嵌入方式特殊或损坏

**解决方案**:
- 已添加空数据检查
- 跳过空图片继续处理

### 问题4: 内存不足

**原因**: 文件太大或图片太多

**解决方案**:
- 禁用图片提取: `extract_images=False`
- 分批处理文档
- 增加系统内存

## 配置选项

### 禁用图片提取（如果遇到问题）

在 `app/routes/upload.py` 中：

```python
ai_parser = AIDocumentParser(
    use_ai=True,
    upload_folder=str(upload_folder),
    extract_images=False  # 禁用图片提取
)
```

### 查看详细日志

解析日志会实时显示：
- 每个步骤的进度百分比
- 检测到的题目
- 图片提取状态
- 任何错误信息

## 测试建议

1. **先用简单文档测试**
   - 只有文本，无图片
   - 标准格式的题目

2. **逐步增加复杂度**
   - 添加图片
   - 添加表格
   - 混合题型

3. **使用诊断工具**
   - `diagnose_parser.py` - 详细诊断
   - `simple_parser_test.py` - 简化测试

## 改进建议

如果仍然遇到问题，可以考虑：

1. **更换Word文档格式**
   - 使用更标准的.docx格式
   - 确保文档完整

2. **手动预处理文档**
   - 删除特殊对象
   - 统一图片格式

3. **使用其他解析方案**
   - Tika (Apache)
   - LibreOffice命令行
   - Pandoc

## 代码位置

- 主解析器: `app/parsers/ai_document_parser.py`
- 上传路由: `app/routes/upload.py`
- 诊断脚本: `diagnose_parser.py`
- 简化测试: `simple_parser_test.py`
