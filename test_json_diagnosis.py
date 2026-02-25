#!/usr/bin/env python3
"""测试JSON截断和修复逻辑"""

import json5
import json
import re

def test_truncated_json():
    """测试被截断的JSON"""
    print("=" * 60)
    print("测试: 被截断的JSON")
    print("=" * 60)

    # 完整的JSON
    full_json = """[
  {"id": 1, "name": "test1"},
  {"id": 2, "name": "test2"},
  {"id": 3, "name": "test3"}
]"""

    # 被截断的JSON（缺少最后的])
    truncated = full_json[:-1]

    print(f"完整JSON长度: {len(full_json)}")
    print(f"截断JSON长度: {len(truncated)}")
    print(f"截断JSON末尾: {repr(truncated[-50:])}")

    print("\n测试完整JSON:")
    try:
        result = json5.loads(full_json)
        print(f"✅ 成功，解析出 {len(result)} 项")
    except Exception as e:
        print(f"❌ 失败: {e}")

    print("\n测试截断JSON:")
    try:
        result = json5.loads(truncated)
        print(f"✅ 成功")
    except Exception as e:
        print(f"❌ 失败: {e}")

def test_with_unescaped_quotes():
    """测试包含未转义双引号的情况"""
    print("\n" + "=" * 60)
    print("测试: 包含未转义双引号的字符串值")
    print("=" * 60)

    # 模拟AI返回的问题JSON - text字段中包含Python代码，代码中有未转义的双引号
    problem_json = """[
  {
    "type": "single_choice",
    "content": "测试题目",
    "options": [
      {
        "id": "A",
        "text": "print("hello world")"
      }
    ]
  }
]"""

    print("测试 json5.loads():")
    try:
        result = json5.loads(problem_json)
        print(f"✅ 成功")
    except Exception as e:
        print(f"❌ 失败: {e}")
        print("这是预期的，因为字符串值中有未转义的双引号")

def test_find_last_bracket():
    """测试查找最后一个]的逻辑"""
    print("\n" + "=" * 60)
    print("测试: 查找最后一个]的逻辑")
    print("=" * 60)

    test_str = """[
  {"id": 1},
  {"id": 2},
  {"id": 3}
]
Extra text here"""

    start_idx = test_str.find('[')
    end_idx = test_str.rfind(']') + 1

    print(f"第一个 [ 在位置: {start_idx}")
    print(f"最后一个 ] 在位置: {end_idx - 1}")
    print(f"提取的JSON长度: {end_idx - start_idx}")

    json_str = test_str[start_idx:end_idx]
    try:
        result = json5.loads(json_str)
        print(f"✅ 成功解析，提取出 {len(result)} 项")
    except Exception as e:
        print(f"❌ 失败: {e}")

def test_json_with_python_code():
    """测试包含复杂Python代码的JSON"""
    print("\n" + "=" * 60)
    print("测试: 包含复杂Python代码的JSON")
    print("=" * 60)

    complex_json = """[
  {
    "type": "single_choice",
    "content": "以下哪个是正确的字典定义？",
    "options": [
      {
        "id": "A",
        "text": "{'name': 'Tom', 'age': 18, 'items': ['a', 'b', 'c']}"
      },
      {
        "id": "B",
        "text": "{'name': 'Tom', \"age\": 18}"
      },
      {
        "id": "C",
        "text": "print(\"test\\nvalue\")"
      }
    ],
    "correct_answer": "A",
    "points": 2
  }
]"""

    print("测试 json5.loads():")
    try:
        result = json5.loads(complex_json)
        print(f"✅ 成功，解析出 {len(result)} 道题")
        print(f"选项A的text: {result[0]['options'][0]['text']}")
        print(f"选项C的text: {result[0]['options'][2]['text']}")
    except Exception as e:
        print(f"❌ 失败: {e}")

def test_actual_problem():
    """模拟实际问题 - AI返回的JSON可能被截断或格式错误"""
    print("\n" + "=" * 60)
    print("测试: 模拟实际问题")
    print("=" * 60)

    # 模拟AI返回的JSON（从日志中提取的问题模式）
    # 问题：可能有未闭合的字符串或括号
    problem_cases = [
        # Case 1: 字符串值中有Python代码，包含未转义的双引号
        """[
  {"type": "single_choice", "options": [{"text": "print("test")"}]}
]""",
        # Case 2: JSON被截断
        """[
  {"type": "single_choice"},
  {"type": "single_choice"}""",
        # Case 3: 反斜杠未正确转义
        """[
  {"text": "a\b"}
]"""
    ]

    for i, case in enumerate(problem_cases, 1):
        print(f"\nCase {i}:")
        print(f"JSON: {case[:100]}...")

        try:
            result = json5.loads(case)
            print(f"✅ json5 成功")
        except Exception as e:
            print(f"❌ json5 失败: {str(e)[:50]}")

        try:
            result = json.loads(case)
            print(f"✅ json 成功")
        except Exception as e:
            print(f"❌ json 失败: {str(e)[:50]}")

if __name__ == "__main__":
    print("JSON解析问题诊断测试\n")

    test_truncated_json()
    test_with_unescaped_quotes()
    test_find_last_bracket()
    test_json_with_python_code()
    test_actual_problem()

    print("\n" + "=" * 60)
    print("结论:")
    print("=" * 60)
    print("1. json5可以处理包含Python代码的JSON（代码中有单引号）")
    print("2. json5无法处理字符串值中有未转义的双引号")
    print("3. 如果JSON被截断，解析会失败")
    print("\n可能的问题原因：")
    print("- AI返回的JSON中，代码示例包含未转义的双引号")
    print("- AI返回的JSON被截断（max_tokens不够）")
    print("- AI返回的JSON格式本身有问题")
