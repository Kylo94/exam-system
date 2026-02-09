"""解析器基础模块

定义文档解析器的抽象接口和基础实现。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
import json


class BaseParser(ABC):
    """文档解析器抽象基类"""
    
    @abstractmethod
    def parse(self, file_path: str) -> Dict[str, Any]:
        """解析文档并返回结构化数据
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            解析后的结构化数据
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持或解析失败
        """
        pass
    
    @abstractmethod
    def extract_questions(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从解析内容中提取问题
        
        Args:
            content: 解析后的文档内容
            
        Returns:
            问题字典列表
        """
        pass
    
    @abstractmethod
    def validate_question(self, question_data: Dict[str, Any]) -> bool:
        """验证问题数据格式
        
        Args:
            question_data: 问题数据字典
            
        Returns:
            是否有效
        """
        pass
    
    def save_to_json(self, data: Dict[str, Any], output_path: str) -> None:
        """将解析结果保存为JSON文件
        
        Args:
            data: 解析数据
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_json(self, json_path: str) -> Dict[str, Any]:
        """从JSON文件加载解析结果
        
        Args:
            json_path: JSON文件路径
            
        Returns:
            解析数据
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息字典
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        return {
            'path': str(path.absolute()),
            'name': path.name,
            'stem': path.stem,
            'suffix': path.suffix,
            'size': path.stat().st_size,
            'modified': path.stat().st_mtime
        }
    
    def supported_formats(self) -> List[str]:
        """获取支持的文件格式
        
        Returns:
            支持的文件扩展名列表
        """
        return []
    
    def can_parse(self, file_path: str) -> bool:
        """检查是否可以解析该文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否可以解析
        """
        path = Path(file_path)
        return path.suffix.lower() in self.supported_formats()