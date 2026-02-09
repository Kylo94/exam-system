"""题目处理工具函数

提供题目类型检测、答案标准化、选项格式化等工具函数。
"""

import re
import json
from typing import Dict, List, Any, Optional, Union


def detect_question_type(text: str) -> str:
    """
    根据题目文本自动检测题型
    
    基于文本特征识别题型，支持以下类型：
    - single_choice: 单选题
    - multiple_choice: 多选题  
    - true_false: 判断题
    - fill_blank: 填空题
    - short_answer: 简答题/主观题
    - programming: 编程题
    
    Args:
        text: 题目文本内容
        
    Returns:
        题型标识字符串，如 'single_choice', 'multiple_choice' 等
        
    Raises:
        ValueError: 当文本为空时
        
    Examples:
        >>> detect_question_type("一、单选题：Python是什么语言？")
        'single_choice'
        >>> detect_question_type("1. 以下哪些是Python的特点？（多选题）")
        'multiple_choice'
    """
    if not text or not text.strip():
        raise ValueError("题目文本不能为空")
    
    text_lower = text.lower().strip()
    
    # 题型关键词映射
    type_patterns = [
        # 单选题
        (r'(单选题|单项选择|单选|single.*choice|single.*select)', 'single_choice'),
        # 多选题
        (r'(多选题|多项选择|多选|multiple.*choice|multiple.*select)', 'multiple_choice'),
        # 判断题
        (r'(判断题|判断|true.*false|judgment)', 'true_false'),
        # 填空题
        (r'(填空题|填空|fill.*blank|fill.*in.*blank)', 'fill_blank'),
        # 编程题
        (r'(编程题|编程|programming|coding)', 'programming'),
        # 简答题/主观题
        (r'(简答题|问答题|主观题|论述题|short.*answer|subjective)', 'short_answer'),
    ]
    
    for pattern, q_type in type_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return q_type
    
    # 根据文本特征推断
    if re.search(r'[A-D]\.\s+|（[A-D]）|\[[A-D]\]', text):
        # 有A. B. C. D. 格式的选项，默认为单选题
        return 'single_choice'
    elif '_____' in text or '______' in text or '（' in text and '）' in text:
        # 有下划线或括号填空
        return 'fill_blank'
    elif re.search(r'(正确|错误|对|错|true|false)', text_lower):
        # 包含判断关键词
        return 'true_false'
    elif re.search(r'(简述|论述|说明|解释|为什么|如何)', text_lower):
        # 主观题特征
        return 'short_answer'
    elif re.search(r'(def |function |class |import |print\()', text_lower):
        # 编程题特征
        return 'programming'
    
    # 默认返回单选题（最常见）
    return 'single_choice'


def normalize_answer(answer: str, question_type: str) -> str:
    """
    标准化答案
    
    根据题型统一答案格式：
    - 判断题：统一为 "正确" 或 "错误"
    - 单选题：统一为大写字母（A, B, C, D）
    - 多选题：统一为逗号分隔的大写字母（A,B,C）
    - 其他题型：去除首尾空格，标准化换行符
    
    Args:
        answer: 原始答案
        question_type: 题型标识
        
    Returns:
        标准化后的答案字符串
        
    Examples:
        >>> normalize_answer("A", "single_choice")
        'A'
        >>> normalize_answer("正确", "true_false")
        '正确'
        >>> normalize_answer("a,b,c", "multiple_choice")
        'A,B,C'
    """
    if not answer:
        return ""
    
    answer = str(answer).strip()
    
    # 根据题型处理
    if question_type == 'true_false':
        # 统一判断题答案
        truth_map = {
            '正确': '正确', '对': '正确', 'true': '正确', 'yes': '正确', '是': '正确',
            '错误': '错误', '错': '错误', 'false': '错误', 'no': '错误', '否': '错误'
        }
        
        for key, value in truth_map.items():
            if answer.lower() == key.lower():
                return value
        
        # 如果无法识别，尝试从常见格式转换
        if answer in ['1', 't', 'T']:
            return '正确'
        elif answer in ['0', 'f', 'F']:
            return '错误'
        
        # 默认返回原始答案
        return answer
    
    elif question_type in ['single_choice', 'multiple_choice']:
        # 处理选择题答案
        if question_type == 'single_choice':
            # 单选题：取第一个有效字母
            match = re.search(r'[A-D]', answer.upper())
            if match:
                return match.group()
            # 如果答案是数字，转换为字母
            if answer.isdigit():
                index = int(answer)
                if 1 <= index <= 4:
                    return chr(ord('A') + index - 1)
        else:
            # 多选题：提取所有有效字母，排序去重
            matches = re.findall(r'[A-D]', answer.upper())
            if matches:
                unique_matches = sorted(set(matches))
                return ','.join(unique_matches)
            # 如果答案是数字列表
            if re.match(r'^\d+(,\d+)*$', answer):
                indices = [int(x) for x in answer.split(',')]
                letters = []
                for idx in indices:
                    if 1 <= idx <= 4:
                        letters.append(chr(ord('A') + idx - 1))
                if letters:
                    return ','.join(sorted(set(letters)))
        
        return answer.upper()
    
    elif question_type == 'fill_blank':
        # 填空题：去除多余空格，但保留中间空格
        return ' '.join(answer.split())
    
    else:
        # 主观题、编程题等：只做基本清理
        return answer.strip()


def format_options(options_data: Union[List, Dict, str]) -> List[Dict[str, Any]]:
    """
    统一格式化选项数据
    
    支持多种输入格式：
    1. 列表格式: ['选项A内容', '选项B内容', ...]
    2. 字典格式: {'A': '选项A内容', 'B': '选项B内容', ...}
    3. JSON字符串: '{"A": "选项A内容", "B": "选项B内容"}'
    4. 文本格式: "A.选项A内容\\nB.选项B内容"
    
    Args:
        options_data: 原始选项数据
        
    Returns:
        标准化的选项列表，格式: [{'id': 'A', 'text': '选项内容'}, ...]
        
    Raises:
        ValueError: 当选项数据格式无效时
        
    Examples:
        >>> format_options(['Python是解释型语言', 'Python是编译型语言'])
        [{'id': 'A', 'text': 'Python是解释型语言'}, {'id': 'B', 'text': 'Python是编译型语言'}]
        
        >>> format_options({'A': '选项A', 'B': '选项B'})
        [{'id': 'A', 'text': '选项A'}, {'id': 'B', 'text': '选项B'}]
    """
    if not options_data:
        return []
    
    # 如果已经是标准格式，直接返回
    if isinstance(options_data, list) and len(options_data) > 0:
        # 检查是否已经是标准格式
        first_item = options_data[0]
        if isinstance(first_item, dict) and 'id' in first_item and 'text' in first_item:
            return options_data
    
    result = []
    
    try:
        # 1. 处理JSON字符串
        if isinstance(options_data, str):
            try:
                data = json.loads(options_data)
                options_data = data
            except json.JSONDecodeError:
                # 不是JSON，可能是文本格式
                pass
        
        # 2. 处理字典格式
        if isinstance(options_data, dict):
            for key, value in options_data.items():
                if isinstance(key, str) and key.strip():
                    option_id = key.strip().upper()
                    option_text = str(value).strip() if value else ""
                    result.append({'id': option_id, 'text': option_text})
        
        # 3. 处理列表格式
        elif isinstance(options_data, list):
            letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
            for i, item in enumerate(options_data):
                if i >= len(letters):
                    break
                option_id = letters[i]
                option_text = str(item).strip() if item else ""
                result.append({'id': option_id, 'text': option_text})
        
        # 4. 处理文本格式
        elif isinstance(options_data, str):
            # 解析 "A.内容 B.内容" 或 "A、内容 B、内容" 格式
            lines = options_data.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 匹配 A.内容 或 A、内容 格式
                match = re.match(r'^([A-Z])[\.、]\s*(.+)$', line)
                if match:
                    option_id = match.group(1)
                    option_text = match.group(2).strip()
                    result.append({'id': option_id, 'text': option_text})
        
        # 按字母顺序排序
        result.sort(key=lambda x: x['id'])
        
        return result
    
    except Exception as e:
        raise ValueError(f"选项数据格式无效: {e}")


def validate_question_data(question_data: Dict[str, Any]) -> bool:
    """
    验证题目数据完整性
    
    Args:
        question_data: 题目数据字典
        
    Returns:
        是否有效
        
    Examples:
        >>> data = {'type': 'single_choice', 'text': '题目', 'correct_answer': 'A'}
        >>> validate_question_data(data)
        True
    """
    required_fields = ['type', 'text', 'correct_answer']
    
    for field in required_fields:
        if field not in question_data or not question_data[field]:
            return False
    
    # 验证题型
    valid_types = ['single_choice', 'multiple_choice', 'true_false', 
                   'fill_blank', 'short_answer', 'programming']
    if question_data['type'] not in valid_types:
        return False
    
    # 验证选择题选项
    if question_data['type'] in ['single_choice', 'multiple_choice']:
        if 'options' not in question_data or not question_data['options']:
            return False
    
    return True


# 测试代码（开发时使用）
if __name__ == "__main__":
    # 测试detect_question_type
    test_cases = [
        "一、单选题：Python是什么语言？",
        "1. 以下哪些是Python的特点？（多选题）",
        "判断题：Python是编译型语言。",
        "填空题：Python诞生于______年。",
        "简答题：简述Python的特点。",
        "编程题：编写一个Python函数计算斐波那契数列。",
    ]
    
    for test in test_cases:
        q_type = detect_question_type(test)
        print(f"文本: {test[:30]}... -> 题型: {q_type}")
    
    # 测试normalize_answer
    print("\n答案标准化测试:")
    print(normalize_answer("A", "single_choice"))  # A
    print(normalize_answer("正确", "true_false"))   # 正确
    print(normalize_answer("a,b,c", "multiple_choice"))  # A,B,C
    print(normalize_answer("1", "single_choice"))  # A
    
    # 测试format_options
    print("\n选项格式化测试:")
    print(format_options(['选项A', '选项B']))
    print(format_options({'A': '选项A', 'B': '选项B'}))
    print(format_options('A.选项A\nB.选项B'))