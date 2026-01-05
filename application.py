"""UESTC 服务系统 - 应用层基类
所有应用模块都应继承自 Application 类
"""

from abc import ABC, abstractmethod
from UESTCAccount import UESTCAccount
from logger import get_logger
from operations import get_operation_manager


class Application(ABC):
    """应用基类，所有模块都应继承此类"""
    
    def __init__(self, name: str, account: UESTCAccount):
        """初始化应用
        
        Args:
            name: 应用名称
            account: 共享的 UESTCAccount 实例
        """
        self.name = name
        self.account = account
        self.logger = get_logger()
        self.operation_manager = get_operation_manager()
    
    @abstractmethod
    def run(self) -> bool:
        """运行应用
        
        Returns:
            运行成功返回 True，失败返回 False
        """
        pass
    
    def log_info(self, msg: str) -> None:
        """打印信息日志"""
        self.logger.info(f"[{self.name}] {msg}")
    
    def log_warning(self, msg: str) -> None:
        """打印警告日志"""
        self.logger.warning(f"[{self.name}] {msg}")
    
    def log_error(self, msg: str) -> None:
        """打印错误日志"""
        self.logger.error(f"[{self.name}] {msg}")
    
    def log_success(self, msg: str) -> None:
        """打印成功日志"""
        self.logger.success(f"[{self.name}] {msg}")
    
    def send_email(self, subject: str, content: str) -> bool:
        """通过操作层发送邮件
        
        Args:
            subject: 邮件主题
            content: 邮件内容
            
        Returns:
            发送成功返回 True，失败返回 False
        """
        return self.operation_manager.send_email(subject, content)
