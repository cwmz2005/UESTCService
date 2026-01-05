"""UESTC 服务系统 - 任务调度器
支持为各个应用模块设置不同的定时策略
"""

import time
import threading
from typing import Optional, Callable, Dict, List
from abc import ABC, abstractmethod
from logger import get_logger


class SchedulePolicy(ABC):
    """定时策略基类"""
    
    @abstractmethod
    def should_run(self, last_run_time: Optional[float]) -> bool:
        """判断是否应该运行任务
        
        Args:
            last_run_time: 上次运行的时间戳，首次运行为 None
            
        Returns:
            应该运行返回 True，否则返回 False
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取策略描述
        
        Returns:
            策略描述字符串
        """
        pass


class IntervalPolicy(SchedulePolicy):
    """间隔定时策略，每隔指定秒数运行一次"""
    
    def __init__(self, interval_seconds: int):
        """初始化间隔策略
        
        Args:
            interval_seconds: 间隔秒数
        """
        if interval_seconds <= 0:
            raise ValueError("间隔秒数必须大于 0")
        self.interval_seconds = interval_seconds
    
    def should_run(self, last_run_time: Optional[float]) -> bool:
        """判断是否应该运行（首次运行或距上次运行超过间隔时间）"""
        if last_run_time is None:
            return True
        return time.time() - last_run_time >= self.interval_seconds
    
    def get_description(self) -> str:
        """获取策略描述"""
        minutes = self.interval_seconds // 60
        seconds = self.interval_seconds % 60
        if minutes > 0:
            return f"每 {minutes} 分 {seconds} 秒"
        else:
            return f"每 {seconds} 秒"


class CronPolicy(SchedulePolicy):
    """Cron 定时策略，按特定时间点运行"""
    
    def __init__(self, hour: int, minute: int):
        """初始化 Cron 策略
        
        Args:
            hour: 小时（0-23）
            minute: 分钟（0-59）
        """
        if not (0 <= hour <= 23):
            raise ValueError("小时必须在 0-23 之间")
        if not (0 <= minute <= 59):
            raise ValueError("分钟必须在 0-59 之间")
        self.hour = hour
        self.minute = minute
    
    def should_run(self, last_run_time: Optional[float]) -> bool:
        """判断是否应该在指定时间运行"""
        import datetime
        now = datetime.datetime.now()
        current_time = (now.hour, now.minute)
        target_time = (self.hour, self.minute)
        
        if current_time < target_time:
            return False
        
        if last_run_time is None:
            return True
        
        # 检查距上次运行是否已超过 1 小时（防止重复运行）
        last_run = datetime.datetime.fromtimestamp(last_run_time)
        return (now - last_run).total_seconds() > 3600
    
    def get_description(self) -> str:
        """获取策略描述"""
        return f"每天 {self.hour:02d}:{self.minute:02d}"


class ScheduledTask:
    """定时任务"""
    
    def __init__(self, name: str, task_func: Callable[[], bool], policy: SchedulePolicy):
        """初始化定时任务
        
        Args:
            name: 任务名称
            task_func: 任务函数，返回 bool 表示执行是否成功
            policy: 定时策略
        """
        self.name = name
        self.task_func = task_func
        self.policy = policy
        self.last_run_time: Optional[float] = None
        self.logger = get_logger()
    
    def execute(self) -> bool:
        """执行任务
        
        Returns:
            任务执行成功返回 True，失败返回 False
        """
        try:
            result = self.task_func()
            self.last_run_time = time.time()
            return result
        except Exception as e:
            self.logger.error(f"任务执行异常: {e}")
            return False
    
    def should_run_now(self) -> bool:
        """判断是否应该立即运行任务"""
        return self.policy.should_run(self.last_run_time)


class Scheduler:
    """任务调度器，管理和运行所有定时任务"""
    
    def __init__(self):
        """初始化调度器"""
        self.tasks: Dict[str, ScheduledTask] = {}
        self.logger = get_logger()
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
    
    def add_task(self, name: str, task_func: Callable[[], bool], policy: SchedulePolicy) -> None:
        """添加定时任务
        
        Args:
            name: 任务名称（唯一标识）
            task_func: 任务函数
            policy: 定时策略
        """
        if name in self.tasks:
            self.logger.warning(f"任务 '{name}' 已存在，将被覆盖")
        
        task = ScheduledTask(name, task_func, policy)
        self.tasks[name] = task
        self.logger.info(f"已添加定时任务: {name} ({policy.get_description()})")
    
    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """获取定时任务
        
        Args:
            name: 任务名称
            
        Returns:
            ScheduledTask 实例，不存在返回 None
        """
        return self.tasks.get(name)
    
    def start(self, check_interval: int = 60) -> None:
        """启动调度器（非阻塞，在后台线程运行）
        
        Args:
            check_interval: 检查任务的间隔秒数
        """
        if self.running:
            self.logger.warning("调度器已在运行")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._run_loop,
            args=(check_interval,),
            daemon=True
        )
        self.scheduler_thread.start()
        self.logger.success(f"调度器已启动（检查间隔: {check_interval}秒）")
    
    def _run_loop(self, check_interval: int) -> None:
        """调度器主循环
        
        Args:
            check_interval: 检查间隔
        """
        self.logger.info(f"调度器主循环启动，管理 {len(self.tasks)} 个任务")
        
        try:
            while self.running:
                for task_name, task in self.tasks.items():
                    if task.should_run_now():
                        self.logger.info(f"执行任务: {task_name}")
                        if task.execute():
                            self.logger.success(f"任务 {task_name} 完成")
                        else:
                            self.logger.warning(f"任务 {task_name} 失败")
                
                time.sleep(check_interval)
        
        except Exception as e:
            self.logger.error(f"调度器异常: {e}")
        finally:
            self.logger.info("调度器已停止")
    
    def stop(self) -> None:
        """停止调度器"""
        if not self.running:
            self.logger.warning("调度器未在运行")
            return
        
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        self.logger.info("调度器已停止")
    
    def run_once_blocking(self) -> int:
        """同步运行所有就绪的任务一次（阻塞式）
        
        Returns:
            成功执行的任务数量
        """
        self.logger.info("开始执行所有就绪任务（同步模式）")
        success_count = 0
        
        for task_name, task in self.tasks.items():
            if task.should_run_now():
                self.logger.info(f"执行任务: {task_name}")
                if task.execute():
                    success_count += 1
                    self.logger.success(f"任务 {task_name} 完成")
                else:
                    self.logger.warning(f"任务 {task_name} 失败")
        
        return success_count
    
    def get_status(self) -> Dict[str, dict]:
        """获取所有任务的状态
        
        Returns:
            任务状态字典
        """
        import datetime
        status = {}
        for task_name, task in self.tasks.items():
            last_run = (
                datetime.datetime.fromtimestamp(task.last_run_time).strftime('%Y-%m-%d %H:%M:%S')
                if task.last_run_time else "从未运行"
            )
            status[task_name] = {
                "policy": task.policy.get_description(),
                "last_run": last_run,
                "should_run_now": task.should_run_now()
            }
        return status
