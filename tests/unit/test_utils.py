"""
Unit tests for the utility functions in app.utils module.
"""

import pytest
from app.utils import (
    detect_question_type,
    normalize_answer,
    format_options,
    validate_question_data,
    get_image_type,
    validate_image_size,
    allowed_file,
    secure_filename,
    validate_file_upload,
)


class TestQuestionUtils:
    """Test cases for question utility functions."""
    
    def test_detect_question_type_keywords(self):
        """Test detecting question types by keywords."""
        test_cases = [
            ("一、单选题：Python是什么语言？", "single_choice"),
            ("1. 以下哪些是Python的特点？（多选题）", "multiple_choice"),
            ("判断题：Python是编译型语言。", "true_false"),
            ("填空题：Python诞生于______年。", "fill_blank"),
            ("简答题：简述Python的特点。", "short_answer"),
            ("编程题：编写一个Python函数计算斐波那契数列。", "programming"),
        ]
        
        for text, expected in test_cases:
            result = detect_question_type(text)
            assert result == expected, f"Failed for: {text[:30]}..."
    
    def test_detect_question_type_patterns(self):
        """Test detecting question types by patterns."""
        test_cases = [
            ("A. 选项A内容 B. 选项B内容", "single_choice"),  # Option pattern
            ("这道题有_____填空", "fill_blank"),  # Underscore pattern
            ("以下说法是否正确？", "true_false"),  # Question pattern
            ("def add(a, b):", "programming"),  # Code pattern
            ("简述Python的特点。", "short_answer"),  # Subjective pattern
        ]
        
        for text, expected in test_cases:
            result = detect_question_type(text)
            assert result == expected, f"Failed for: {text[:30]}..."
    
    def test_detect_question_type_empty(self):
        """Test detecting question type with empty input."""
        with pytest.raises(ValueError, match="题目文本不能为空"):
            detect_question_type("")
        with pytest.raises(ValueError, match="题目文本不能为空"):
            detect_question_type("   ")
    
    def test_normalize_answer_single_choice(self):
        """Test normalizing single choice answers."""
        test_cases = [
            ("A", "A"),
            ("b", "B"),
            ("1", "A"),
            ("2", "B"),
            ("3", "C"),
            ("4", "D"),
            ("invalid", "A"),  # Extracts 'A' from the word
        ]
        
        for answer, expected in test_cases:
            result = normalize_answer(answer, "single_choice")
            assert result == expected, f"Failed for: {answer}"
    
    def test_normalize_answer_multiple_choice(self):
        """Test normalizing multiple choice answers."""
        test_cases = [
            ("a,b,c", "A,B,C"),
            ("C,B,A", "A,B,C"),  # Should be sorted
            ("1,2,3", "A,B,C"),
            ("a,a,b", "A,B"),  # Should deduplicate
            ("invalid", "A,D"),  # Extracts 'A' and 'D' from the word
        ]
        
        for answer, expected in test_cases:
            result = normalize_answer(answer, "multiple_choice")
            assert result == expected, f"Failed for: {answer}"
    
    def test_normalize_answer_true_false(self):
        """Test normalizing true/false answers."""
        test_cases = [
            ("正确", "正确"),
            ("对", "正确"),
            ("true", "正确"),
            ("是", "正确"),
            ("1", "正确"),
            ("t", "正确"),
            ("错误", "错误"),
            ("错", "错误"),
            ("false", "错误"),
            ("否", "错误"),
            ("0", "错误"),
            ("f", "错误"),
            ("unknown", "unknown"),  # Unknown format returns as-is
        ]
        
        for answer, expected in test_cases:
            result = normalize_answer(answer, "true_false")
            assert result == expected, f"Failed for: {answer}"
    
    def test_normalize_answer_other_types(self):
        """Test normalizing answers for other question types."""
        # Fill blank
        result = normalize_answer("  Python  解释型  ", "fill_blank")
        assert result == "Python 解释型"
        
        # Short answer
        result = normalize_answer("  前后空格  ", "short_answer")
        assert result == "前后空格"
        
        # Programming
        result = normalize_answer("  def func():  ", "programming")
        assert result == "def func():"
    
    def test_format_options_list(self):
        """Test formatting options from list."""
        input_data = ['Python是解释型语言', 'Python是编译型语言', 'Python既是解释型也是编译型']
        result = format_options(input_data)
        
        assert len(result) == 3
        assert result[0]['id'] == 'A'
        assert result[0]['text'] == 'Python是解释型语言'
        assert result[1]['id'] == 'B'
        assert result[2]['id'] == 'C'
    
    def test_format_options_dict(self):
        """Test formatting options from dictionary."""
        input_data = {'A': '选项A内容', 'B': '选项B内容', 'C': '选项C内容'}
        result = format_options(input_data)
        
        assert len(result) == 3
        assert result[0]['id'] == 'A'
        assert result[0]['text'] == '选项A内容'
        assert result[1]['id'] == 'B'
        assert result[2]['id'] == 'C'
    
    def test_format_options_text(self):
        """Test formatting options from text."""
        input_data = 'A.选项A内容\nB.选项B内容\nC.选项C内容'
        result = format_options(input_data)
        
        assert len(result) == 3
        assert result[0]['id'] == 'A'
        assert result[0]['text'] == '选项A内容'
        assert result[1]['id'] == 'B'
        assert result[2]['id'] == 'C'
    
    def test_format_options_json(self):
        """Test formatting options from JSON string."""
        input_data = '{"A": "选项A", "B": "选项B"}'
        result = format_options(input_data)
        
        assert len(result) == 2
        assert result[0]['id'] == 'A'
        assert result[0]['text'] == '选项A'
        assert result[1]['id'] == 'B'
    
    def test_format_options_empty(self):
        """Test formatting empty options."""
        result = format_options(None)
        assert result == []
        
        result = format_options([])
        assert result == []
    
    def test_validate_question_data_valid(self):
        """Test validating valid question data."""
        valid_data = {
            'type': 'single_choice',
            'text': 'Python是什么语言？',
            'correct_answer': 'A',
            'options': ['解释型语言', '编译型语言', '混合型语言']
        }
        
        assert validate_question_data(valid_data) is True
    
    def test_validate_question_data_invalid(self):
        """Test validating invalid question data."""
        # Missing required field
        invalid_missing = {
            'type': 'single_choice',
            'text': 'Python是什么语言？'
            # Missing correct_answer
        }
        assert validate_question_data(invalid_missing) is False
        
        # Invalid question type
        invalid_type = {
            'type': 'invalid_type',
            'text': '题目',
            'correct_answer': '答案'
        }
        assert validate_question_data(invalid_type) is False
        
        # Missing options for choice questions
        invalid_no_options = {
            'type': 'single_choice',
            'text': '题目',
            'correct_answer': 'A'
            # Missing options
        }
        assert validate_question_data(invalid_no_options) is False


class TestImageUtils:
    """Test cases for image utility functions."""
    
    def test_get_image_type(self):
        """Test getting image type from filename."""
        test_cases = [
            ("image.jpg", "jpeg"),
            ("photo.png", "png"),
            ("animation.gif", "gif"),
            ("diagram.bmp", "bmp"),
            ("icon.svg", "svg"),
            ("unknown.txt", "unknown"),
            ("", "unknown"),
        ]
        
        for filename, expected in test_cases:
            result = get_image_type(filename)
            assert result == expected, f"Failed for: {filename}"
    
    def test_validate_image_size(self):
        """Test validating image size."""
        # Small but invalid image data
        small_data = b'fake_image_data' * 10  # ~140 bytes, not a valid image
        assert validate_image_size(small_data, max_size=5242880) is False
        
        # Large data beyond limit
        large_data = b'fake_image_data' * 1000000  # ~14MB
        assert validate_image_size(large_data, max_size=5242880) is False
        
        # Empty data
        assert validate_image_size(b'', max_size=100) is False
        
        # Invalid data (not an image)
        invalid_data = b'not_an_image'
        assert validate_image_size(invalid_data, max_size=5242880) is False


class TestFileUtils:
    """Test cases for file utility functions."""
    
    def test_allowed_file(self):
        """Test checking allowed file extensions."""
        extensions = {'.docx', '.pdf', '.txt'}
        
        test_cases = [
            ("exam.docx", True),
            ("document.pdf", True),
            ("notes.txt", True),
            ("image.jpg", False),
            ("data.xlsx", False),
            ("", False),
            (None, False),
        ]
        
        for filename, expected in test_cases:
            if filename is None:
                result = allowed_file(filename, extensions)
            else:
                result = allowed_file(filename, extensions)
            assert result == expected, f"Failed for: {filename}"
    
    def test_secure_filename(self):
        """Test generating secure filenames."""
        test_cases = [
            ("../../etc/passwd", "etc_passwd"),  # Path traversal
            ("normal-file_name.pdf", "normal-file_name.pdf"),  # Normal name
            ("file with spaces.txt", "file_with_spaces.txt"),  # Spaces
            # Note: Chinese filename test may need adjustment based on system
        ]
        
        for filename, expected in test_cases:
            result = secure_filename(filename)
            assert result == expected, f"Failed for: {filename}"
    
    def test_validate_file_upload_mock(self):
        """Test validating file upload with mock objects."""
        
        class MockFile:
            def __init__(self, filename):
                self.filename = filename
                self._pos = 0
            
            def tell(self):
                return self._pos
            
            def seek(self, pos, whence=0):
                if whence == 2:
                    self._pos = 1000  # Simulate file size
                return self._pos
        
        # Valid file
        mock_file = MockFile("test.docx")
        result, message = validate_file_upload(mock_file, allowed_extensions={'.docx', '.pdf'})
        assert result is True
        assert "验证通过" in message
        
        # Invalid extension
        mock_file = MockFile("test.jpg")
        result, message = validate_file_upload(mock_file, allowed_extensions={'.docx', '.pdf'})
        assert result is False
        assert "不支持的文件类型" in message
        
        # Empty filename
        mock_file = MockFile("")
        result, message = validate_file_upload(mock_file)
        assert result is False
        assert "文件名不能为空" in message
        
        # No file object
        result, message = validate_file_upload(None)
        assert result is False
        assert "没有上传文件" in message


if __name__ == "__main__":
    """Allow running tests directly for debugging."""
    pytest.main([__file__, "-v"])