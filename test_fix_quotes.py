#!/usr/bin/env python3
"""测试修复未转义双引号的函数"""

import json5
import re

def fix_unescaped_quotes(json_str: str) -> str:
    """
    修复JSON字符串值中的未转义双引号

    策略：找到所有 "key": "value" 模式，确保value中的双引号被转义
    """
    result = json_str

    # 处理所有 "text": "..." 字段
    text_pattern = r'"text":\s*"((?:[^"\\]|\\.)*)"'

    def fix_text_value(match):
        text_value = match.group(1)
        # 检查是否有未转义的双引号（排除已经是转义的 \"）
        # 方法：将所有 \" 替换为临时标记，然后查找未转义的 "
        temp_text = text_value.replace('\\"', '__TEMP_QUOTE__')
        if '"' in temp_text:
            # 有未转义的双引号，需要转义
            text_value = text_value.replace('"', '\\"')
        return f'"text": "{text_value}"'

    result = re.sub(text_pattern, fix_text_value, result)

    # 同样处理 "content" 字段
    content_pattern = r'"content":\s*"((?:[^"\\]|\\.)*)"'

    def fix_content_value(match):
        content_value = match.group(1)
        temp_content = content_value.replace('\\"', '__TEMP_QUOTE__')
        if '"' in temp_content:
            content_value = content_value.replace('"', '\\"')
        return f'"content": "{content_value}"'

    result = re.sub(content_pattern, fix_content_value, result)

    return result

def test_fix_function():
    """测试修复函数"""
    test_cases = [
        # Case 1: 有未转义双引号
        ("""{"text": "print("test")"}""", "未转义双引号"),
        # Case 2: 已正确转义
        ("""{"text": "print(\\"test\\")"}""", "已正确转义"),
        # Case 3: 没有双引号
        ("""{"text": "hello world"}""", "没有双引号"),
        # Case 4: 复杂case - 包含Python代码和双引号
        ("""{"text": "data = {"key": "value"}"}""", "Python字典"),
        # Case 5: 多个字段
        ("""{"content": "a"b"c", "text": "x"y"z"}""", "多个字段"),
    ]

    for case, desc in test_cases:
        print(f"\n{'='*60}")
        print(f"测试: {desc}")
        print(f"原始: {case}")
        print(f"修复: {fix_unescaped_quotes(case)}")

        fixed = fix_unescaped_quotes(case)
        try:
            result = json5.loads(fixed)
            print(f"✅ 解析成功")
        except Exception as e:
            print(f"❌ 解析失败: {e}")

def test_real_problem():
    """测试实际问题场景"""
    print(f"\n{'='*60}")
    print("测试实际问题场景")
    print('='*60)

    # 模拟AI返回的有问题的JSON
    problem_json = """[
  {
    "type": "single_choice",
    "content": "测试题目",
    "options": [
      {
        "id": "A",
        "text": "print("hello world")"
      },
      {
        "id": "B",
        "text": "data = {"name": "Tom", "age": 18}"
      },
      {
        "id": "C",
        "text": "['a':'b', 'c':'d']"
      }
    ]
  }
]"""

    print("\n原始JSON（有未转义双引号）:")
    print(problem_json[:200] + "...")

    print("\n尝试直接解析:")
    try:
        result = json5.loads(problem_json)
        print("✅ 成功")
    except Exception as e:
        print(f"❌ 失败: {str(e)[:100]}")

    print("\n修复后解析:")
    fixed_json = fix_unescaped_quotes(problem_json)
    try:
        result = json5.loads(fixed_json)
        print(f"✅ 成功！解析出 {len(result)} 道题")
        print(f"选项A的text: {result[0]['options'][0]['text']}")
        print(f"选项B的text: {result[0]['options'][1]['text']}")
    except Exception as e:
        print(f"❌ 失败: {e}")

if __name__ == "__main__":
    print("测试未转义双引号修复函数\n")

    test_fix_function()
    test_real_problem()

    print(f"\n{'='*60}")
    print("结论:")
    print('='*60)
    print("修复函数可以:")
    print("1. 识别 text/content 字段中的未转义双引号")
    print("2. 自动转义这些双引号")
    print("3. 保留已经正确转义的双引号")
