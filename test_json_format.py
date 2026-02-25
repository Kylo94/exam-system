"""测试JSON格式保留空格和换行符"""

import json
import json5

# 测试数据：模拟AI返回的包含代码的JSON
test_json_str = """
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
        "type": "single_choice",
        "content": "Python中以下哪个关键字用于定义函数？",
        "options": [
            {"id": "A", "text": "function", "has_image": false},
            {"id": "B", "text": "def", "has_image": false},
            {"id": "C", "text": "func", "has_image": false},
            {"id": "D", "text": "define", "has_image": false}
        ],
        "correct_answer": "B",
        "points": 2,
        "explanation": "def是Python中定义函数的关键字",
        "knowledge_point": "Python基础语法",
        "content_has_image": false,
        "order_index": 2
    }
]
"""

print("=" * 60)
print("测试1: 标准JSON解析（使用json模块）")
print("=" * 60)

try:
    data = json.loads(test_json_str)
    print("✓ JSON解析成功")
    print(f"题目数量: {len(data)}")
    
    # 检查第一题的内容
    question1_content = data[0]['content']
    print(f"\n第一题内容长度: {len(question1_content)} 字符")
    print(f"是否包含换行符 '\\n': {('\\n' in question1_content)}")
    print(f"换行符数量: {question1_content.count('\\n')}")
    
    print("\n第一题内容（前200字符）:")
    print(repr(question1_content[:200]))
    
    print("\n第一题完整内容:")
    print(question1_content)
    
    # 检查代码格式
    if "def find_max" in question1_content:
        print("\n✓ 找到代码块")
        lines = question1_content.split('\\n')
        print(f"代码行数: {len([l for l in lines if 'def' in l or l.strip()])}")
        
        # 显示代码部分
        for i, line in enumerate(question1_content.split('\\n')):
            if 'def' in line or (i > 0 and any(keyword in line for keyword in ['if', 'for', 'return'])):
                print(f"  {line[:80]}")

except Exception as e:
    print(f"✗ JSON解析失败: {e}")


print("\n" + "=" * 60)
print("测试2: json5解析（更宽松的JSON格式）")
print("=" * 60)

try:
    data5 = json5.loads(test_json_str)
    print("✓ json5解析成功")
    print(f"题目数量: {len(data5)}")
    
    question1_content5 = data5[0]['content']
    print(f"\n第一题内容长度: {len(question1_content5)} 字符")
    print(f"换行符数量: {question1_content5.count('\\n')}")
    
except Exception as e:
    print(f"✗ json5解析失败: {e}")


print("\n" + "=" * 60)
print("测试3: Python实际换行符 vs JSON转义")
print("=" * 60)

real_text = "第一行\n第二行\n第三行"
print(f"实际Python字符串: {repr(real_text)}")
print(f"长度: {len(real_text)}")
print(f"换行符数量: {real_text.count(chr(10))}")

# 转换为JSON
json_encoded = json.dumps({"text": real_text})
print(f"\nJSON编码后: {json_encoded}")

# 从JSON解析回
json_decoded = json.loads(json_encoded)
print(f"JSON解码后: {repr(json_decoded['text'])}")
print(f"是否与原文本一致: {json_decoded['text'] == real_text}")


print("\n" + "=" * 60)
print("测试4: 代码缩进保留")
print("=" * 60)

code_text = """
def hello():
    print("Hello")
    if True:
        print("World")
"""

json_with_code = json.dumps({"code": code_text}, ensure_ascii=False)
print(f"JSON编码的代码: {json_with_code}")

decoded = json.loads(json_with_code)
print(f"\n解码后的代码:")
print(decoded['code'])

# 检查缩进
lines = decoded['code'].split('\n')
indented_lines = [line for line in lines if line.startswith('    ') or line.startswith('\t')]
print(f"\n缩进行数: {len(indented_lines)}")
print(f"✓ 代码缩进保留成功" if len(indented_lines) > 0 else "✗ 代码缩进丢失")
