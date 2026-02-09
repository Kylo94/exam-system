"""文本文件解析器

用于解析纯文本格式的试题。
"""

import re
from typing import Dict, List, Any
from pathlib import Path

from .base import BaseParser


class TextParser(BaseParser):
    """纯文本文件解析器"""
    
    def parse(self, file_path: str) -> Dict[str, Any]:
        """解析文本文件
        
        Args:
            file_path: 文本文件路径
            
        Returns:
            解析后的文档数据
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        file_info = self.get_file_info(file_path)
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        
        # 分割行
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # 提取问题
        questions = self._extract_questions_from_lines(lines)
        
        result = {
            'file_info': file_info,
            'metadata': {
                'line_count': len(lines),
                'question_count': len(questions),
                'format': 'text'
            },
            'content': {
                'lines': lines,
                'full_text': content
            },
            'questions': questions
        }
        
        return result
    
    def extract_questions(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从解析内容中提取问题
        
        Args:
            content: 解析后的文档内容
            
        Returns:
            问题字典列表
        """
        return content.get('questions', [])
    
    def validate_question(self, question_data: Dict[str, Any]) -> bool:
        """验证问题数据格式
        
        Args:
            question_data: 问题数据字典
            
        Returns:
            是否有效
        """
        # 使用基类的通用验证
        from .docx_parser import DocxParser
        return DocxParser().validate_question(question_data)
    
    def supported_formats(self) -> List[str]:
        """获取支持的文件格式
        
        Returns:
            支持的文件扩展名列表
        """
        return ['.txt', '.text']
    
    def _extract_questions_from_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        """从文本行中提取问题
        
        Args:
            lines: 文本行列表
            
        Returns:
            问题字典列表
        """
        questions = []
        current_question = None
        current_options = []
        in_question = False
        question_number = 1
        
        for line in lines:
            # 检查是否是问题开始
            is_question = self._is_question_line(line)
            is_option = self._is_option_line(line)
            
            if is_question:
                # 保存前一个问题
                if current_question:
                    questions.append(current_question)
                
                # 开始新问题
                question_text = self._clean_question_line(line)
                q_type = self._detect_question_type(question_text)
                
                current_question = {
                    'number': question_number,
                    'content': question_text,
                    'type': q_type,
                    'score': 1.0,
                    'options': {'choices': []},
                    'correct_answer': None,
                    'explanation': '',
                    'raw_lines': [line]
                }
                
                current_options = []
                in_question = True
                question_number += 1
            
            elif in_question and is_option:
                # 处理选项
                option_text = self._clean_option_line(line)
                current_options.append(option_text)
                current_question['raw_lines'].append(line)
                current_question['options']['choices'] = current_options
            
            elif in_question and line:
                # 可能是问题内容的延续
                current_question['raw_lines'].append(line)
                
                # 检查答案或解析
                if self._contains_answer(line):
                    answer = self._extract_answer(line)
                    if answer:
                        if current_question['type'] == 'single_choice':
                            current_question['correct_answer'] = self._normalize_single_answer(answer)
                        elif current_question['type'] == 'multiple_choice':
                            current_question['correct_answer'] = self._normalize_multiple_answer(answer)
                
                elif self._contains_explanation(line):
                    current_question['explanation'] = line
        
        # 添加最后一个问题
        if current_question:
            questions.append(current_question)
        
        return questions
    
    def _is_question_line(self, line: str) -> bool:
        """检查是否是问题行
        
        Args:
            line: 文本行
            
        Returns:
            是否是问题行
        """
        patterns = [
            r'^\d+[\.、]',          # 1. 或 1、
            r'^\(\d+\)',            # (1)
            r'^第\d+题',            # 第1题
            r'^[一二三四五六七八九十]+[\.、]',  # 一、 二.
            r'^[Qq]\.?\s*\d+',      # Q1, q.1
            r'^题目\d+',             # 题目1
        ]
        
        return any(re.match(pattern, line) for pattern in patterns)
    
    def _is_option_line(self, line: str) -> bool:
        """检查是否是选项行
        
        Args:
            line: 文本行
            
        Returns:
            是否是选项行
        """
        patterns = [
            r'^[A-D][\.、]',        # A. 或 A、
            r'^[①②③④⑤⑥]',        # ① ②
            r'^\(\w+\)',            # (A) (B)
            r'^[a-d][\.\)]',        # a) a.
        ]
        
        return any(re.match(pattern, line) for pattern in patterns)
    
    def _clean_question_line(self, line: str) -> str:
        """清理问题行，移除编号
        
        Args:
            line: 原始问题行
            
        Returns:
            清理后的问题文本
        """
        patterns = [
            r'^\d+[\.、]',
            r'^\(\d+\)',
            r'^第\d+题',
            r'^[一二三四五六七八九十]+[\.、]',
            r'^[Qq]\.?\s*\d+\s*[\.、]?',
            r'^题目\d+\s*[\.、]?',
        ]
        
        for pattern in patterns:
            line = re.sub(pattern, '', line)
        
        return line.strip()
    
    def _clean_option_line(self, line: str) -> str:
        """清理选项行，移除选项标记
        
        Args:
            line: 原始选项行
            
        Returns:
            清理后的选项文本
        """
        patterns = [
            r'^[A-D][\.、]',
            r'^[①②③④⑤⑥]',
            r'^\(\w+\)',
            r'^[a-d][\.\)]',
        ]
        
        for pattern in patterns:
            line = re.sub(pattern, '', line)
        
        return line.strip()
    
    def _detect_question_type(self, question_text: str) -> str:
        """检测问题类型
        
        Args:
            question_text: 问题文本
            
        Returns:
            问题类型
        """
        text_lower = question_text.lower()
        
        # 判断题特征
        if re.search(r'(是否正确|对不对|判断.*正误|true.*false|正确.*错误)', text_lower):
            return 'true_false'
        
        # 填空题特征
        if re.search(r'(填空|______|_+|\s+_+\s+|\[.*\])', text_lower):
            return 'fill_blank'
        
        # 简答题特征
        if re.search(r'(简述|论述|分析|说明|解释|为什么|如何|怎样|原因|意义|影响)', text_lower):
            return 'short_answer'
        
        # 多选题特征
        if re.search(r'(多选|哪些|多个|不止一个|所有.*正确)', text_lower):
            return 'multiple_choice'
        
        # 默认单选题
        return 'single_choice'
    
    def _contains_answer(self, line: str) -> bool:
        """检查是否包含答案
        
        Args:
            line: 文本行
            
        Returns:
            是否包含答案
        """
        patterns = [
            r'答案',
            r'正确答案',
            r'参考[答案]',
            r'answer',
            r'correct',
        ]
        
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns)
    
    def _contains_explanation(self, line: str) -> bool:
        """检查是否包含解析
        
        Args:
            line: 文本行
            
        Returns:
            是否包含解析
        """
        patterns = [
            r'解析',
            r'说明',
            r'解释',
            r'explanation',
            r'note',
        ]
        
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns)
    
    def _extract_answer(self, line: str) -> str:
        """提取答案
        
        Args:
            line: 包含答案的文本行
            
        Returns:
            提取的答案
        """
        patterns = [
            r'[答案|正确答案][：:]\s*([A-D①②③④]+)',
            r'answer[：:]\s*([A-D①②③④]+)',
            r'correct[：:]\s*([A-D①②③④]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ''
    
    def _normalize_single_answer(self, answer: str) -> str:
        """标准化单选题答案
        
        Args:
            answer: 原始答案
            
        Returns:
            标准化答案
        """
        if not answer:
            return ''
        
        answer = answer.strip().upper()
        
        mapping = {
            '①': 'A', '②': 'B', '③': 'C', '④': 'D',
            '⑤': 'E', '⑥': 'F', '1': 'A', '2': 'B',
            '3': 'C', '4': 'D',
        }
        
        if answer in mapping:
            return mapping[answer]
        
        match = re.search(r'[A-H]', answer)
        if match:
            return match.group(0)
        
        return answer[0] if answer else ''
    
    def _normalize_multiple_answer(self, answer: str) -> List[str]:
        """标准化多选题答案
        
        Args:
            answer: 原始答案
            
        Returns:
            标准化答案列表
        """
        if not answer:
            return []
        
        answer = answer.strip().upper()
        answers = []
        
        for char in answer:
            if char.isalpha() and 'A' <= char <= 'H':
                answers.append(char)
        
        return list(set(answers))