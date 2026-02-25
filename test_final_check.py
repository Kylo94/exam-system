#!/usr/bin/env python3
"""最终检查 - 模拟实际场景"""

import json5

# 从日志中复制的实际AI返回数据（包含Python代码，只有单引号）
real_case = """[
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
  }
]"""

print("="*60)
print("测试: 从日志中提取的实际AI返回数据")
print("="*60)

print(f"\nJSON长度: {len(real_case)} 字符")
print(f"JSON最后100字符: {repr(real_case[-100:])}")

print("\n尝试用 json5 解析:")
try:
    result = json5.loads(real_case)
    print(f"✅ 成功！解析出 {len(result)} 道题")
    print(f"第1题类型: {result[0]['type']}")
    print(f"第1题内容长度: {len(result[0]['content'])} 字符")
    print(f"选项A的text: {result[0]['options'][0]['text']}")
except Exception as e:
    print(f"❌ 失败: {e}")
    print(f"错误类型: {type(e).__name__}")

# 测试如果JSON被截断会怎样
print("\n" + "="*60)
print("测试: 如果JSON被截断（去掉最后10个字符）")
print("="*60)

truncated = real_case[:-10]
print(f"截断后长度: {len(truncated)} 字符")
print(f"截断后最后50字符: {repr(truncated[-50:])}")

try:
    result = json5.loads(truncated)
    print(f"✅ 成功")
except Exception as e:
    print(f"❌ 失败: {e}")
    print(f"错误类型: {type(e).__name__}")

# 测试如果JSON中有未闭合的字符串
print("\n" + "="*60)
print("测试: 如果JSON中有未闭合的字符串")
print("="*60)

unclosed_string = """[
  {
    "type": "single_choice",
    "content": "测试"
  }
"""
# 缺少最后的 ]

try:
    result = json5.loads(unclosed_string)
    print(f"✅ 成功")
except Exception as e:
    print(f"❌ 失败: {e}")
    print(f"错误类型: {type(e).__name__}")
