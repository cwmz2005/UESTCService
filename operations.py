"""UESTC 服务系统 - 操作层
提供通用操作接口，如发邮件等
"""

from abc import ABC, abstractmethod
from logger import get_logger
import yagmail


class Operation(ABC):
    """操作基类"""
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> bool:
        """执行操作
        
        Returns:
            操作成功返回 True，失败返回 False
        """
        pass


class EmailOperation(Operation):
    """邮件发送操作"""
    
    def __init__(self, email_user: str, email_pass: str, email_to: str):
        """初始化邮件操作
        
        Args:
            email_user: 发件邮箱
            email_pass: 邮箱授权码
            email_to: 收件邮箱
        """
        self.email_user = email_user
        self.email_pass = email_pass
        self.email_to = email_to
        self.logger = get_logger()
    
    def execute(self, subject: str, content: str) -> bool:
        """发送邮件
        
        Args:
            subject: 邮件主题
            content: 邮件内容
            
        Returns:
            发送成功返回 True，失败返回 False
        """
        try:
            yag = yagmail.SMTP(
                user=self.email_user,
                password=self.email_pass,
                host='smtp.163.com'
            )
            yag.send(to=self.email_to, subject=subject, contents=content)
            self.logger.success(f"邮件已发送: {subject}")
            return True
        except Exception as e:
            self.logger.error(f"发送邮件失败: {e}")
            return False


class OperationManager:
    """操作管理器，统一管理所有操作"""
    
    def __init__(self):
        """初始化操作管理器"""
        self.operations = {}
        self.logger = get_logger()
    
    def register_operation(self, name: str, operation: Operation) -> None:
        """注册操作
        
        Args:
            name: 操作名称
            operation: Operation 实例
        """
        self.operations[name] = operation
        self.logger.info(f"已注册操作: {name}")
    
    def get_operation(self, name: str) -> Operation:
        """获取操作
        
        Args:
            name: 操作名称
            
        Returns:
            Operation 实例
            
        Raises:
            KeyError: 操作不存在
        """
        if name not in self.operations:
            raise KeyError(f"操作 '{name}' 不存在")
        return self.operations[name]
    
    def send_email(self, subject: str, content: str) -> bool:
        """便捷方法：发送邮件
        
        Args:
            subject: 邮件主题
            content: 邮件内容
            
        Returns:
            发送成功返回 True，失败返回 False
        """
        try:
            email_op = self.get_operation("email")
            return email_op.execute(subject, content)
        except KeyError:
            self.logger.error("邮件操作未注册")
            return False


# 全局操作管理器实例
_global_operation_manager = None


def get_operation_manager() -> OperationManager:
    """获取全局操作管理器实例
    
    Returns:
        OperationManager 实例
    """
    global _global_operation_manager
    if _global_operation_manager is None:
        _global_operation_manager = OperationManager()
    return _global_operation_manager
