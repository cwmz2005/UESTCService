"""UESTC 服务系统 - 日志模块
提供统一的日志管理功能，同时支持写入日志文件和邮件告警
"""

import time
import os
from typing import Optional, Callable
from datetime import datetime
from typing import Any


class Logger:
    """统一的日志管理器，支持控制台输出、文件保存和邮件告警"""
    
    def __init__(self, name: str = "UESTCService", log_dir: str = "log"):
        """初始化日志管理器
        
        Args:
            name: 日志器名称
            log_dir: 日志文件夹路径
        """
        self.name = name
        self.log_dir = log_dir
        self.error_alert_handler: Optional[Callable[[str, str], None]] = None
        self.warning_alert_handler: Optional[Callable[[str, str], None]] = None
        
        # 创建日志文件夹
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def set_error_alert_handler(self, handler: Callable[[str, str], Any]) -> None:
        """设置错误告警处理器
        
        Args:
            handler: 处理器函数，接收 (标题, 内容) 两个参数
        """
        self.error_alert_handler = handler
    
    def set_warning_alert_handler(self, handler: Callable[[str, str], Any]) -> None:
        """设置警告告警处理器
        
        Args:
            handler: 处理器函数，接收 (标题, 内容) 两个参数
        """
        self.warning_alert_handler = handler
    
    def _get_log_file_path(self) -> str:
        """获取今天的日志文件路径
        
        Returns:
            日志文件的完整路径
        """
        today = datetime.now().strftime('%Y-%m-%d')
        return os.path.join(self.log_dir, f"{today}.log")
    
    def _write_to_file(self, msg: str) -> None:
        """将日志写入文件
        
        Args:
            msg: 日志消息
        """
        try:
            log_file = self._get_log_file_path()
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(msg + '\n')
        except Exception as e:
            print(f"[WARNING] 写入日志文件失败: {e}")
    
    def log(self, msg: str, level: str = "INFO") -> None:
        """打印带时间戳和级别的日志信息，同时写入文件
        
        Args:
            msg: 日志信息
            level: 日志级别 (INFO, WARNING, ERROR, SUCCESS)
        """
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        level_str = f"[{level}]"
        formatted_msg = f"[{timestamp}] {level_str} {msg}"
        
        # 打印到控制台
        print(formatted_msg)
        
        # 写入到文件
        self._write_to_file(formatted_msg)
    
    def info(self, msg: str) -> None:
        """打印信息级别日志"""
        self.log(msg, "INFO")
    
    def warning(self, msg: str) -> None:
        """打印警告级别日志，同时触发警告告警"""
        self.log(msg, "WARNING")
        
        # 触发警告告警处理器
        if self.warning_alert_handler:
            try:
                subject = f"【系统警告】{self.name}"
                content = f"警告信息: {msg}\n\n发生时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n此为系统自动告警邮件，请勿回复。"
                self.warning_alert_handler(subject, content)
            except Exception as e:
                print(f"[WARNING] 警告告警发送失败: {e}")
    
    def error(self, msg: str) -> None:
        """打印错误级别日志，同时触发错误告警"""
        self.log(msg, "ERROR")
        
        # 触发错误告警处理器
        if self.error_alert_handler:
            try:
                subject = f"【系统错误】{self.name}"
                content = f"错误信息: {msg}\n\n发生时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n此为系统自动告警邮件，请勿回复。"
                self.error_alert_handler(subject, content)
            except Exception as e:
                print(f"[WARNING] 错误告警发送失败: {e}")
    
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
