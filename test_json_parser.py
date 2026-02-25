#!/usr/bin/env python3
"""测试JSON解析器"""

import json5
import json
import ast

# 模拟AI返回的JSON（包含Python代码示例）
test_json = """[
  {
    "type": "single_choice",
    "content": "老师要求大家记住四大名著的作者，小明机智地想到了可以用字典进行记录，以下哪个选项的字典格式是正确？（ ）",
    "options": [
      {
        "id": "A",
        "text": "['曹雪芹':'红楼梦', '吴承恩':'西游记', '罗贯中':'三国演义', '施耐庵:'水浒传']",
        "has_image": false
      },
      {
        "id": "B",
        "text": "{'曹雪芹'-'红楼梦', '吴承恩'-'西游记', '罗贯中'-'三国演义', '施耐庵-'水浒传'}",
        "has_image": false
      },
      {
        "id": "C",
        "text": "{'曹雪芹':'红楼梦'; '吴承恩':'西游记'; '罗贯中':'三国演义'; '施耐庵:'水浒传'}",
        "has_image": false
      },
      {
        "id": "D",
        "text": "{'曹雪芹':'红楼梦', '吴承恩':'西游记', '罗贯中':'三国演义', '施耐庵':'水浒传'}",
        "has_image": false
      }
    ],
    "correct_answer": "D",
    "points": 2,
    "explanation": "字典是用大括号括起来的，排除 A;字典中键值对中间是冒号，排除B，字典每个键值对之间，要用逗号隔开，排除 C",
    "knowledge_point": "字典格式和语法",
    "content_has_image": false,
    "order_index": 1
  },
  {
    "type": "single_choice",
    "content": "已知列表a = [11,222, 333 ,4444]，以下能输出333的代码是？（ ）",
    "options": [
      {"id": "A", "text": "print(a[-1])", "has_image": false},
      {"id": "B", "text": "print(a[3])", "has_image": false},
      {"id": "C", "text": "print(a[333])", "has_image": false},
      {"id": "D", "text": "print(a[2])", "has_image": false}
    ],
    "correct_answer": "D",
    "points": 2,
    "explanation": "列表的索引是从0开始，如果是反索引，则是从-1开始，所以本题的答案为D",
    "knowledge_point": "列表索引",
    "content_has_image": false,
    "order_index": 2
  },
  {
    "type": "true_false",
    "content": "Python中的列表是有序的，集合是无序的。",
    "options": [],
    "correct_answer": "true",
    "points": 1,
    "explanation": "列表是有序序列，集合是无序集合",
    "knowledge_point": "数据结构特性",
    "content_has_image": false,
    "order_index": 3
  }
]"""

def test_json5():
    """测试json5解析"""
    print("=" * 60)
    print("测试 1: json5.loads()")
    print("=" * 60)
    try:
        result = json5.loads(test_json)
        print(f"✅ 成功！解析出 {len(result)} 道题")
        print(f"第1题内容: {result[0]['content'][:50]}...")
        print(f"第1题选项A的text: {result[0]['options'][0]['text']}")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        return False

def test_standard_json():
    """测试标准JSON解析"""
    print("\n" + "=" * 60)
    print("测试 2: json.loads()")
    print("=" * 60)
    try:
        result = json.loads(test_json)
        print(f"✅ 成功！解析出 {len(result)} 道题")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

def test_ast_literal_eval():
    """测试ast.literal_eval"""
    print("\n" + "=" * 60)
    print("测试 3: ast.literal_eval()")
    print("=" * 60)
    try:
        result = ast.literal_eval(test_json)
        print(f"✅ 成功！解析出 {len(result)} 道题")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

def test_problematic_case():
    """测试有问题的case - 包含未转义的双引号"""
    print("\n" + "=" * 60)
    print("测试 4: 包含未转义双引号的case")
    print("=" * 60)

    problematic = """[
      {
        "type": "single_choice",
        "content": "题目包含\"双引号\"",
        "options": [{"id": "A", "text": "选项内容"}]
      }
    ]"""

    print("测试 json5.loads():")
    try:
        result = json5.loads(problematic)
        print(f"✅ 成功")
    except Exception as e:
        print(f"❌ 失败: {e}")

    print("\n测试 json.loads():")
    try:
        result = json.loads(problematic)
        print(f"✅ 成功")
    except Exception as e:
        print(f"❌ 失败: {e}")

def test_with_single_quotes_in_value():
    """测试值中包含单引号"""
    print("\n" + "=" * 60)
    print("测试 5: 值中包含单引号")
    print("=" * 60)

    single_quote_case = """[
      {
        "type": "single_choice",
        "content": "题目",
        "options": [{"id": "A", "text": "It's a test"}]
      }
    ]"""

    print("测试 json5.loads():")
    try:
        result = json5.loads(single_quote_case)
        print(f"✅ 成功，text内容: {result[0]['options'][0]['text']}")
    except Exception as e:
        print(f"❌ 失败: {e}")

if __name__ == "__main__":
    print("JSON解析器测试\n")

    test_json5()
    test_standard_json()
    test_ast_literal_eval()
    test_problematic_case()
    test_with_single_quotes_in_value()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
