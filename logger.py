"""UESTC 服务系统 - 日志模块
提供统一的日志管理功能
"""

import time
from typing import Optional


class Logger:
    """统一的日志管理器"""
    
    def __init__(self, name: str = "UESTCService"):
        """初始化日志管理器
        
        Args:
            name: 日志器名称
        """
        self.name = name
    
    def log(self, msg: str, level: str = "INFO") -> None:
        """打印带时间戳和级别的日志信息
        
        Args:
            msg: 日志信息
            level: 日志级别 (INFO, WARNING, ERROR, SUCCESS)
        """
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        level_str = f"[{level}]"
        print(f"[{timestamp}] {level_str} {msg}")
    
    def info(self, msg: str) -> None:
        """打印信息级别日志"""
        self.log(msg, "INFO")
    
    def warning(self, msg: str) -> None:
        """打印警告级别日志"""
        self.log(msg, "WARNING")
    
    def error(self, msg: str) -> None:
        """打印错误级别日志"""
        self.log(msg, "ERROR")
    
    def success(self, msg: str) -> None:
        """打印成功级别日志"""
        self.log(msg, "SUCCESS")


# 全局日志实例
_global_logger: Optional[Logger] = None


def get_logger(name: str = "UESTCService") -> Logger:
    """获取全局日志实例
    
    Args:
        name: 日志器名称（仅首次调用时有效）
        
    Returns:
        Logger 实例
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger(name)
    return _global_logger
