#!/usr/bin/env python3
"""改进的未转义双引号修复函数"""

import json5
import re

def fix_unescaped_quotes_improved(json_str: str) -> str:
    """
    改进的修复JSON字符串值中的未转义双引号

    使用不同的策略：直接扫描整个JSON，找到字符串值中的未转义双引号
    """
    result = []

    i = 0
    in_string = False
    in_key = False
    escape_next = False
    current_key = None

    while i < len(json_str):
        char = json_str[i]

        if escape_next:
            # 如果前一个字符是反斜杠，当前字符应该原样输出
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == '\\':
            # 遇到反斜杠，标记下一个字符需要转义
            result.append(char)
            escape_next = True
            i += 1
            continue

        if char == '"':
            if not in_string:
                # 开始字符串
                in_string = True
                in_key = (i > 0 and json_str[i-1] in ': \t\n' or
                         (i == 0) or
                         (i > 0 and json_str[i-1] == '{') or
                         (i > 0 and json_str[i-1] == '[' and
                          (i < 2 or json_str[i-2] in ' \t\n,')))
                result.append(char)
            elif in_key:
                # 结束key
                in_key = False
                in_string = True
                result.append(char)
            else:
                # 结束value
                in_string = False
                result.append(char)
            i += 1
            continue

        if in_string and not in_key:
            # 在字符串值中
            # 将双引号转义
            if char == '"':
                result.append('\\"')
            else:
                result.append(char)
        else:
            result.append(char)

        i += 1

    return ''.join(result)

def test_improved_fix():
    """测试改进的修复函数"""
    test_cases = [
        ("""{"text": "print("test")"}""", "未转义双引号"),
        ("""{"text": "print(\\"test\\")"}""", "已正确转义"),
        ("""{"text": "hello world"}""", "没有双引号"),
        ("""{"text": "data = {"key": "value"}"}""", "Python字典"),
        ("""{"content": "a"b"c", "text": "x"y"z"}""", "多个字段"),
    ]

    for case, desc in test_cases:
        print(f"\n{'='*60}")
        print(f"测试: {desc}")
        print(f"原始: {case}")

        fixed = fix_unescaped_quotes_improved(case)
        print(f"修复: {fixed}")

        try:
            result = json5.loads(fixed)
            print(f"✅ 解析成功")
        except Exception as e:
            print(f"❌ 解析失败: {e}")

def test_real_problem_improved():
    """测试实际问题场景"""
    print(f"\n{'='*60}")
    print("测试实际问题场景（改进版）")
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

    print("\n尝试直接解析原始JSON:")
    try:
        result = json5.loads(problem_json)
        print("✅ 成功")
    except Exception as e:
        print(f"❌ 失败: {str(e)[:100]}")

    print("\n使用改进的修复函数:")
    fixed_json = fix_unescaped_quotes_improved(problem_json)
    print(f"修复后（前300字符）: {fixed_json[:300]}...")

    try:
        result = json5.loads(fixed_json)
        print(f"✅ 成功！解析出 {len(result)} 道题")
        print(f"选项A的text: {result[0]['options'][0]['text']}")
        print(f"选项B的text: {result[0]['options'][1]['text']}")
    except Exception as e:
        print(f"❌ 失败: {e}")

if __name__ == "__main__":
    print("测试改进的未转义双引号修复函数\n")

    test_improved_fix()
    test_real_problem_improved()
