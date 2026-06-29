"""UESTC 服务系统 - 日志模块
提供统一的日志管理功能，同时支持写入日志文件和邮件告警
"""

import time
import os
from contextlib import contextmanager
from typing import Optional, Callable, List, Dict
from datetime import datetime
from typing import Any


class _AlertSuppression:
    """告警抑制控制器，由 suppress_alerts() 上下文管理器创建。

    收集被抑制的告警，提供 flush() / discard() 让调用方在获知最终结果后决定：
    - 任务最终成功 → discard() 丢弃被抑制的告警
    - 任务最终失败 → flush(logger) 将被抑制告警释放到聚合管道
    """

    def __init__(self):
        self.buffer: list[dict] = []
        self._resolved = False

    def discard(self) -> None:
        """丢弃所有被抑制的告警（任务最终成功，期间告警无意义）。"""
        if not self._resolved:
            self.buffer.clear()
            self._resolved = True

    def flush(self, logger: 'Logger') -> None:
        """将被抑制的告警释放到 Logger 的聚合管道（任务最终失败）。"""
        if not self._resolved:
            if self.buffer:
                logger.pending_alerts.extend(self.buffer)
                self.buffer.clear()
                if logger._should_send_aggregated_alerts():
                    logger._send_aggregated_alerts()
            self._resolved = True


class Logger:
    """统一的日志管理器，支持控制台输出、文件保存和邮件告警。"""

    def __init__(self, name: str = "UESTCService", log_dir: str = "log", error_aggregate_window: int = 300):
        """初始化日志管理器。

        Args:
            name: 日志器名称
            log_dir: 日志文件夹路径
            error_aggregate_window: 错误/警告聚合时间窗口（秒），默认 5 分钟
        """
        self.name = name
        self.log_dir = log_dir
        self.error_alert_handler: Optional[Callable[[str, str], None]] = None
        self.warning_alert_handler: Optional[Callable[[str, str], None]] = None

        # 告警聚合（error + warning 统一管道）
        self.aggregate_window = error_aggregate_window
        self.pending_alerts: List[Dict[str, str]] = []
        self.last_alert_send_time: Optional[float] = None

        # 告警抑制栈（嵌套 suppress_alerts 调用时内层收集到栈顶）
        self._suppression_stack: List[_AlertSuppression] = []

        # 创建日志文件夹
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    # ------------------------------------------------------------------
    # 告警抑制 API（产业级可复用方案）
    # ------------------------------------------------------------------

    @contextmanager
    def suppress_alerts(self):
        """创建告警抑制上下文。

        在上下文中产生的所有 error / warning 不会进入聚合管道，而是暂存在抑制
        缓冲区中。上下文退出后，调用方可通过控制器决定：

            with logger.suppress_alerts() as sup:
                result = do_something()
                if result:
                    sup.discard()   # 成功 → 丢弃缓冲告警

            if not result:
                # 可在此做重试 …
                if retry_success:
                    sup.discard()
                else:
                    sup.flush(logger)  # 最终失败 → 释放到聚合管道

        若上下文因异常退出，缓冲告警自动 flush（不丢失）。
        """
        suppression = _AlertSuppression()
        self._suppression_stack.append(suppression)
        try:
            yield suppression
        except Exception:
            # 异常退出：释放缓冲告警（不要静默丢失）
            suppression.flush(self)
            raise
        finally:
            self._suppression_stack.pop()

    # ------------------------------------------------------------------
    # Handler 注册
    # ------------------------------------------------------------------

    def set_error_alert_handler(self, handler: Callable[[str, str], Any]) -> None:
        """设置错误告警处理器。"""
        self.error_alert_handler = handler

    def set_warning_alert_handler(self, handler: Callable[[str, str], Any]) -> None:
        """设置警告告警处理器。"""
        self.warning_alert_handler = handler

    # ------------------------------------------------------------------
    # 文件写入
    # ------------------------------------------------------------------

    def _get_log_file_path(self) -> str:
        """获取今天的日志文件路径。"""
        today = datetime.now().strftime('%Y-%m-%d')
        return os.path.join(self.log_dir, f"{today}.log")

    def _write_to_file(self, msg: str) -> None:
        """将日志写入文件。"""
        try:
            log_file = self._get_log_file_path()
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(msg + '\n')
        except Exception as e:
            print(f"[WARNING] 写入日志文件失败: {e}")

    # ------------------------------------------------------------------
    # 日志输出
    # ------------------------------------------------------------------

    def log(self, msg: str, level: str = "INFO") -> None:
        """打印带时间戳和级别的日志，同时写入文件。"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        level_str = f"[{level}]"
        formatted_msg = f"[{timestamp}] {level_str} {msg}"

        print(formatted_msg, flush=True)
        self._write_to_file(formatted_msg)

    def info(self, msg: str) -> None:
        """INFO 级别日志（不触发告警）。"""
        self.log(msg, "INFO")

    def warning(self, msg: str) -> None:
        """WARNING 级别日志，进入聚合管道。"""
        self.log(msg, "WARNING")
        self._enqueue_alert("WARNING", msg)

    def error(self, msg: str) -> None:
        """ERROR 级别日志，进入聚合管道。"""
        self.log(msg, "ERROR")
        self._enqueue_alert("ERROR", msg)

    def success(self, msg: str) -> None:
        """SUCCESS 级别日志。"""
        self.log(msg, "SUCCESS")

    # ------------------------------------------------------------------
    # 告警聚合内部实现
    # ------------------------------------------------------------------

    def _enqueue_alert(self, level: str, msg: str) -> None:
        """将告警入队：优先路由到活跃的抑制上下文，否则进入全局聚合队列。"""
        if not self.error_alert_handler and not self.warning_alert_handler:
            return

        alert_record = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': level,
            'message': msg,
            '_time': time.time(),
        }

        # 路由到最内层未决的抑制上下文
        for suppression in reversed(self._suppression_stack):
            if not suppression._resolved:
                suppression.buffer.append(alert_record)
                return

        # 无活跃抑制 → 进入全局聚合队列
        self.pending_alerts.append(alert_record)
        if self._should_send_aggregated_alerts():
            self._send_aggregated_alerts()

    def _should_send_aggregated_alerts(self) -> bool:
        """基于最早待发告警的等待时间判断是否应发送聚合邮件。"""
        if not self.pending_alerts:
            return False
        oldest_time = min(a['_time'] for a in self.pending_alerts)
        return time.time() - oldest_time >= self.aggregate_window

    def _send_aggregated_alerts(self) -> None:
        """发送聚合告警邮件。"""
        if not self.pending_alerts:
            return

        handler = self.error_alert_handler or self.warning_alert_handler
        if not handler:
            return

        try:
            alert_count = len(self.pending_alerts)
            error_count = sum(1 for a in self.pending_alerts if a['level'] == 'ERROR')
            warning_count = sum(1 for a in self.pending_alerts if a['level'] == 'WARNING')

            parts = []
            if error_count > 0:
                parts.append(f"{error_count} 个错误")
            if warning_count > 0:
                parts.append(f"{warning_count} 个警告")
            subject = f"【系统告警汇总】{self.name} - {'、'.join(parts)}"

            content_parts = [
                f"在过去 {self.aggregate_window // 60} 分钟内，系统累计发生了 {alert_count} 条告警：",
                f"  - 错误: {error_count} 条",
                f"  - 警告: {warning_count} 条",
                "",
                "=" * 60,
                "",
            ]

            for idx, alert in enumerate(self.pending_alerts, 1):
                content_parts.append(f"告警 {idx} [{alert['level']}]:")
                content_parts.append(f"  时间: {alert['timestamp']}")
                content_parts.append(f"  消息: {alert['message']}")
                content_parts.append("")

            content_parts.append("=" * 60)
            content_parts.append("")
            content_parts.append("此为系统自动告警邮件，请勿回复。")

            content = "\n".join(content_parts)
            handler(subject, content)

            self.pending_alerts.clear()
            self.last_alert_send_time = time.time()

        except Exception as e:
            print(f"[WARNING] 聚合告警邮件发送失败: {e}")

    def tick(self) -> None:
        """定期检查：若有待发告警已超过聚合窗口，立即发送。

        供调度器空闲循环等场景周期性调用，确保告警不会因无后续事件而无限滞留。
        """
        if self.pending_alerts and self._should_send_aggregated_alerts():
            self._send_aggregated_alerts()

    def flush_errors(self) -> None:
        """立即发送所有待聚合的告警（用于程序退出等场景）。"""
        if self.pending_alerts:
            self._send_aggregated_alerts()


# ------------------------------------------------------------------
# 全局日志实例
# ------------------------------------------------------------------

_global_logger: Optional[Logger] = None


def get_logger(name: str = "UESTCService") -> Logger:
    """获取全局 Logger 实例（首次调用时创建）。"""
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger(name)
    return _global_logger
