"""测试完整流程：AI解析后JSON中是否保留换行和缩进"""

import json
import json5

# 模拟AI返回的完整响应（包含markdown代码块）
# 注意：实际AI返回的JSON字符串中，换行符会被转义为\n
ai_response = """```json
[
    {
        "type": "short_answer",
        "content": "请编写一个Python函数，实现以下功能：\\n1. 输入一个整数列表\\n2. 返回列表中的最大值\\n3. 处理空列表的情况\\n\\n示例代码：\\ndef find_max(numbers):\\n    if not numbers:\\n        return None\\n    max_num = numbers[0]\\n    for num in numbers[1:]:\\n        if num > max_num:\\n            max_num = num\\n    return max_num",
        "correct_answer": "见代码实现",
        "points": 10,
        "explanation": "使用循环遍历列表，逐个比较找到最大值",
        "knowledge_point": "列表遍历和条件判断",
        "content_has_image": false,
        "order_index": 1
    },
    {
        "type": "short_answer",
        "content": "简述Python中的列表推导式。\\n要求1：写出基本语法\\n要求2：给出一个示例\\n要求3：说明优缺点",
        "correct_answer": "列表推导式是Python中创建列表的简洁方式",
        "points": 8,
        "explanation": "列表推导式可以替代for循环和map/filter函数",
        "knowledge_point": "Python高级特性",
        "content_has_image": false,
        "order_index": 2
    }
]
```
"""

print("=" * 70)
print("测试：模拟AI解析完整流程")
print("=" * 70)

# 步骤1：移除markdown代码块标记
import re
json_str = re.sub(r'```json\s*', '', ai_response)
json_str = json_str.replace('```', '')
print(f"\n步骤1 - 移除markdown后长度: {len(json_str)} 字符")

# 步骤2：提取JSON数组
start_idx = json_str.find('[')
end_idx = json_str.rfind(']') + 1
if start_idx >= 0 and end_idx > start_idx:
    json_str = json_str[start_idx:end_idx]
    print(f"步骤2 - 提取JSON数组后长度: {len(json_str)} 字符")

# 步骤3：解析JSON
try:
    questions = json.loads(json_str)
    print(f"\n✓ JSON解析成功，共 {len(questions)} 道题")
    
    # 检查第一题
    q1 = questions[0]
    content = q1['content']
    
    print(f"\n第一题分析:")
    print(f"  - 题型: {q1['type']}")
    print(f"  - 分值: {q1['points']}")
    print(f"  - 内容长度: {len(content)} 字符")
    print(f"  - 实际换行符数量: {content.count(chr(10))}")
    print(f"  - 是否包含代码: {'def find_max' in content}")
    
    print(f"\n第一题完整内容:")
    print("-" * 60)
    print(content)
    print("-" * 60)
    
    # 检查代码缩进
    if "    if" in content:
        print("\n✓ 代码4空格缩进保留成功")
    
    # 检查多要求格式
    q2 = questions[1]
    content2 = q2['content']
    print(f"\n第二题分析:")
    print(f"  - 题型: {q2['type']}")
    print(f"  - 内容长度: {len(content2)} 字符")
    print(f"  - 换行符数量: {content2.count(chr(10))}")
    
    print(f"\n第二题完整内容:")
    print("-" * 60)
    print(content2)
    print("-" * 60)
    
    # 检查要求分隔
    if "\n要求1：" in content2 or "要求1：" in content2:
        print("\n✓ 多要求格式正确，使用了换行符")
    
    # 序列化回JSON，验证是否能正确保留
    print("\n" + "=" * 70)
    print("验证：将解析结果序列化回JSON")
    print("=" * 70)
    
    json_output = json.dumps(questions, ensure_ascii=False, indent=2)
    print(f"\n序列化后的JSON长度: {len(json_output)} 字符")
    
    # 重新解析验证
    questions_roundtrip = json.loads(json_output)
    print(f"往返解析成功: {questions_roundtrip[0]['content'] == content}")
    
except Exception as e:
    print(f"\n✗ JSON解析失败: {e}")
    import traceback
    traceback.print_exc()

# 测试不同场景
print("\n" + "=" * 70)
print("测试不同场景的代码格式保留")
print("=" * 70)

test_cases = [
    ("Python代码", """def test():
    print("Hello")
    return 1
"""),
    ("Java代码", """public void test() {
    System.out.println("Hello");
}"""),
    ("多行文本", """第一行
第二行
第三行"""),
    ("制表符缩进", """def test():
\tpass
"""),
]

for name, text in test_cases:
    json_str = json.dumps({"content": text}, ensure_ascii=False)
    decoded = json.loads(json_str)
    preserved = decoded['content'] == text
    print(f"\n{name}: {'✓ 保留' if preserved else '✗ 丢失'}")
    if not preserved:
        print(f"  原始: {repr(text[:50])}")
        print(f"  解码: {repr(decoded['content'][:50])}")
