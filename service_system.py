"""UESTC 服务系统 - 核心框架
管理账户、日志、操作层和应用模块
"""

import os
from typing import List, Dict, Tuple
from UESTCAccount import UESTCAccount
from logger import get_logger
from operations import get_operation_manager, EmailOperation
from application import Application
from scheduler import Scheduler, SchedulePolicy, IntervalPolicy


class UESTCServiceSystem:
    """UESTC 定时服务系统核心框架"""
    
    def __init__(self, username: str, password: str, email_config: Dict[str, str]):
        """初始化服务系统
        
        Args:
            username: UESTC 用户名
            password: UESTC 密码
            email_config: 邮件配置字典，包含 'user', 'password', 'to' 键
        """
        self.logger = get_logger("UESTCServiceSystem")
        self.operation_manager = get_operation_manager()
        
        # 账户层：初始化共享账户
        self.account = UESTCAccount(
            username=username,
            password=password,
            log_func=self.logger.info
        )
        
        # 操作层：注册邮件操作
        email_op = EmailOperation(
            email_user=email_config.get('user', ''),
            email_pass=email_config.get('password', ''),
            email_to=email_config.get('to', '')
        )
        self.operation_manager.register_operation("email", email_op)
        
        # 配置日志告警处理器
        self.logger.set_error_alert_handler(
            lambda subject, content: self.operation_manager.send_email(subject, content)
        )
        self.logger.set_warning_alert_handler(
            lambda subject, content: self.operation_manager.send_email(subject, content)
        )
        
        # 应用层：注册的应用列表
        self.applications: List[Application] = []
        
        # 调度层：任务调度器
        self.scheduler = Scheduler()
        
        # 应用定时配置：{应用名称: 定时策略}
        self.app_schedules: Dict[str, SchedulePolicy] = {}
        
        self.logger.success("服务系统初始化完成")
    
    def register_application(self, app: Application) -> None:
        """注册应用模块
        
        Args:
            app: Application 实例
        """
        self.applications.append(app)
        self.logger.info(f"已注册应用: {app.name}")
    
    def set_app_schedule(self, app_name: str, policy: SchedulePolicy) -> None:
        """为应用设置定时策略
        
        Args:
            app_name: 应用名称
            policy: SchedulePolicy 实例
        """
        self.app_schedules[app_name] = policy
        self.logger.info(f"为应用 {app_name} 设置定时: {policy.get_description()}")
    
    def login(self) -> bool:
        """执行账户登录
        
        Returns:
            登录成功返回 True，失败返回 False
        """
        self.logger.info("开始登录...")
        if self.account.login():
            self.logger.success("账户登录成功")
            return True
        else:
            self.logger.error("账户登录失败")
            return False
    
    def run_all_applications(self) -> int:
        """运行所有已注册的应用模块
        
        Returns:
            成功运行的应用数量
        """
        if not self.applications:
            self.logger.warning("未注册任何应用模块")
            return 0
        
        self.logger.info(f"开始运行 {len(self.applications)} 个应用模块...")
        success_count = 0
        
        for app in self.applications:
            try:
                self.logger.info(f"运行应用: {app.name}")
                if app.run():
                    success_count += 1
                    self.logger.success(f"应用 {app.name} 运行成功")
                else:
                    self.logger.warning(f"应用 {app.name} 运行失败")
            except Exception as e:
                self.logger.error(f"应用 {app.name} 执行异常: {e}")
        
        return success_count
    
    def start_scheduler(self, check_interval: int = 60) -> None:
        """启动定时调度器
        
        Args:
            check_interval: 调度检查间隔（秒）
        """
        if not self.applications:
            self.logger.warning("未注册任何应用模块，无法启动调度器")
            return
        
        # 为所有应用注册定时任务
        for app in self.applications:
            # 如果未设置定时策略，使用默认策略（每小时执行一次）
            policy = self.app_schedules.get(app.name, IntervalPolicy(3600))
            self.scheduler.add_task(app.name, app.run, policy)
        
        # 启动调度器
        self.scheduler.start(check_interval=check_interval)
    
    def stop_scheduler(self) -> None:
        """停止定时调度器"""
        self.scheduler.stop()
    
    def get_scheduler_status(self) -> Dict[str, dict]:
        """获取调度器状态
        
        Returns:
            所有任务的状态信息
        """
        return self.scheduler.get_status()
    
    @staticmethod
    def from_environment() -> 'UESTCServiceSystem':
        """从环境变量创建服务系统实例
        
        需要的环境变量：
        - UESTC_USERNAME: UESTC 用户名
        - UESTC_PASSWORD: UESTC 密码
        - EMAIL_USER: 邮箱地址
        - EMAIL_PASSWORD: 邮箱授权码
        - EMAIL_TO: 收件邮箱
        
        Returns:
            UESTCServiceSystem 实例
            
        Raises:
            RuntimeError: 缺少必要的环境变量
        """
        from dotenv import load_dotenv
        
        load_dotenv()
        
        username = os.getenv('UESTC_USERNAME', '')
        password = os.getenv('UESTC_PASSWORD', '')
        email_user = os.getenv('EMAIL_USER', '')
        email_pass = os.getenv('EMAIL_PASSWORD', '')
        email_to = os.getenv('EMAIL_TO', '')
        
        # 验证必要配置
        missing = []
        if not username:
            missing.append('UESTC_USERNAME')
        if not password:
            missing.append('UESTC_PASSWORD')
        if not email_user:
            missing.append('EMAIL_USER')
        if not email_pass:
            missing.append('EMAIL_PASSWORD')
        if not email_to:
            missing.append('EMAIL_TO')
        
        if missing:
            raise RuntimeError(f"缺少环境变量: {', '.join(missing)}")
        
        return UESTCServiceSystem(
            username=username,
            password=password,
            email_config={
                'user': email_user,
                'password': email_pass,
                'to': email_to
            }
        )
