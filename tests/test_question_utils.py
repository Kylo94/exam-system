"""
题目工具函数测试
"""
import pytest
from app.utils.question_utils import (
    detect_question_type,
    normalize_answer,
    format_options,
    validate_question_data,
)


class TestDetectQuestionType:
    """题目类型检测测试"""

    def test_single_choice(self):
        """测试单选题检测"""
        assert detect_question_type("单选题：Python是什么？") == "single_choice"
        assert detect_question_type("单选：以下正确的是") == "single_choice"
        assert detect_question_type("Single Choice Question") == "single_choice"

    def test_multiple_choice(self):
        """测试多选题检测"""
        assert detect_question_type("多选题：以下哪些正确？") == "multiple_choice"
        assert detect_question_type("Multiple Choice") == "multiple_choice"

    def test_true_false(self):
        """测试判断题检测"""
        assert detect_question_type("判断题：Python是编译型语言") == "true_false"
        assert detect_question_type("True or False") == "true_false"

    def test_fill_blank(self):
        """测试填空题检测"""
        assert detect_question_type("填空题：Python诞生于____年") == "fill_blank"
        assert detect_question_type("Fill in the blank") == "fill_blank"

    def test_short_answer(self):
        """测试简答题检测"""
        assert detect_question_type("简答题：简述Python的特点") == "short_answer"
        assert detect_question_type("问答题：如何理解面向对象") == "short_answer"

    def test_programming(self):
        """测试编程题检测"""
        assert detect_question_type("编程题：实现快速排序") == "programming"
        assert detect_question_type("Programming: Write a function") == "programming"

    def test_option_letters(self):
        """测试通过选项格式检测单选题"""
        assert detect_question_type("A. 选项A\nB. 选项B") == "single_choice"

    def test_default_single_choice(self):
        """测试默认返回单选题"""
        assert detect_question_type("这是一道普通的题目文本") == "single_choice"

    def test_empty_text_raises(self):
        """测试空文本抛出异常"""
        with pytest.raises(ValueError, match="不能为空"):
            detect_question_type("")


class TestNormalizeAnswer:
    """答案标准化测试"""

    def test_single_choice_uppercase(self):
        """测试单选题答案大写"""
        assert normalize_answer("a", "single_choice") == "A"
        assert normalize_answer("B", "single_choice") == "B"

    def test_single_choice_from_digit(self):
        """测试单选题数字转字母"""
        assert normalize_answer("1", "single_choice") == "A"
        assert normalize_answer("2", "single_choice") == "B"
        assert normalize_answer("3", "single_choice") == "C"
        assert normalize_answer("4", "single_choice") == "D"

    def test_multiple_choice_sorted(self):
        """测试多选题排序"""
        assert normalize_answer("c,b,a", "multiple_choice") == "A,B,C"

    def test_multiple_choice_digit(self):
        """测试多选题数字格式"""
        assert normalize_answer("1,2,3", "multiple_choice") == "A,B,C"

    def test_true_false_correct(self):
        """测试判断题正确"""
        assert normalize_answer("正确", "true_false") == "正确"
        assert normalize_answer("对", "true_false") == "正确"
        assert normalize_answer("true", "true_false") == "正确"
        assert normalize_answer("yes", "true_false") == "正确"

    def test_true_false_incorrect(self):
        """测试判断题错误"""
        assert normalize_answer("错误", "true_false") == "错误"
        assert normalize_answer("错", "true_false") == "错误"
        assert normalize_answer("false", "true_false") == "错误"

    def test_fill_blank_whitespace(self):
        """测试填空题空白处理"""
        assert normalize_answer("  2024  ", "fill_blank") == "2024"

    def test_empty_answer(self):
        """测试空答案"""
        assert normalize_answer("", "single_choice") == ""


class TestFormatOptions:
    """选项格式化测试"""

    def test_list_format(self):
        """测试列表格式"""
        result = format_options(['选项A', '选项B', '选项C'])
        assert len(result) == 3
        assert result[0] == {'id': 'A', 'text': '选项A'}

    def test_dict_format(self):
        """测试字典格式"""
        result = format_options({'A': '内容A', 'B': '内容B'})
        assert len(result) == 2
        assert result[0]['id'] == 'A'
        assert result[0]['text'] == '内容A'

    def test_json_string(self):
        """测试JSON字符串"""
        result = format_options('{"A": "内容A", "B": "内容B"}')
        assert len(result) == 2

    def test_text_format(self):
        """测试文本格式"""
        result = format_options("A.内容A\nB.内容B")
        assert len(result) == 2
        assert result[0]['text'] == '内容A'

    def test_empty_returns_empty_list(self):
        """测试空数据返回空列表"""
        assert format_options(None) == []
        assert format_options([]) == []

    def test_standard_format_unchanged(self):
        """测试标准格式保持不变"""
        standard = [{'id': 'A', 'text': '内容A'}]
        assert format_options(standard) == standard


class TestValidateQuestionData:
    """题目数据验证测试"""

    def test_valid_single_choice(self):
        """测试有效单选题"""
        data = {
            'type': 'single_choice',
            'text': 'Python是什么语言？',
            'correct_answer': 'A',
            'options': ['A. 编译型', 'B. 解释型', 'C. 混合型', 'D. 汇编型']
        }
        assert validate_question_data(data) is True

    def test_valid_short_answer(self):
        """测试有效简答题"""
        data = {
            'type': 'short_answer',
            'text': '简述Python的特点',
            'correct_answer': '简洁、易读、易学'
        }
        assert validate_question_data(data) is True

    def test_missing_type(self):
        """测试缺少type字段"""
        data = {
            'text': '题目',
            'correct_answer': 'A'
        }
        assert validate_question_data(data) is False

    def test_missing_text(self):
        """测试缺少text字段"""
        data = {
            'type': 'single_choice',
            'correct_answer': 'A'
        }
        assert validate_question_data(data) is False

    def test_invalid_type(self):
        """测试无效题型"""
        data = {
            'type': 'invalid_type',
            'text': '题目',
            'correct_answer': 'A'
        }
        assert validate_question_data(data) is False

    def test_choice_without_options(self):
        """测试选择题没有选项"""
        data = {
            'type': 'single_choice',
            'text': '题目',
            'correct_answer': 'A'
        }
        assert validate_question_data(data) is False