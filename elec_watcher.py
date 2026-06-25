"""UESTC 宿舍用电监控应用"""

import json
from datetime import date, datetime
from application import Application
from UESTCAccount import UESTCAccount


class ElecWatcherApp(Application):
    """宿舍用电监控应用，当电费余额低于阈值时发送邮件提醒
    失败提醒策略：只有在一天内一次也没有成功获取数据时，才发送邮件告警
    """

    def __init__(self, account: UESTCAccount, threshold: float = 10.0):
        """初始化电费监控应用

        Args:
            account: 共享的 UESTCAccount 实例
            threshold: 电费余额阈值（元），低于此值发送提醒
        """
        super().__init__("ElecWatcher", account)
        self.threshold = threshold
        self.power_url = "https://online.uestc.edu.cn/site/bedroom"
        self.refresh_url = r"https://idas.uestc.edu.cn/authserver/login?service=https%3A%2F%2Fonline.uestc.edu.cn%2Fcommon%2FactionCasLogin%3Fredirect_url%3Dhttps%253A%252F%252Fonline.uestc.edu.cn%252Fpage%252F"

        # 每日失败告警状态追踪
        self._last_success_date: date | None = None          # 上次成功获取数据的日期
        self._daily_failure_alert_sent_date: date | None = None  # 当天已发送失败告警的日期
        self._daily_alert_cutoff_hour: int = 20  # 每天超过此时间(20点)仍未成功则发送告警
    
    def _refresh_session(self) -> bool:
        """刷新会话令牌
        失败时使用 log_info 而非 log_error/log_warning，避免每次失败都触发邮件告警

        Returns:
            刷新成功返回 True，失败返回 False
        """
        try:
            refresh_response = self.account.session.get(self.refresh_url)
            if refresh_response.status_code != 200:
                self.log_info("会话刷新失败，尝试重新登录")
                if not self.account.login():
                    self.log_info("重新登录失败")
                    return False
            return True
        except Exception as e:
            self.log_info(f"刷新会话异常: {e}")
            return False
    
    def _fetch_power_data(self) -> dict:
        """获取宿舍用电数据
        失败时使用 log_info 而非 log_error，避免每次失败都触发邮件告警

        Returns:
            包含电费数据的字典，获取失败返回空字典
        """
        try:
            if not self._refresh_session():
                return {}

            response = self.account.session.get(self.power_url, timeout=10)
            if response.status_code != 200:
                self.log_info(f"请求失败，状态码: {response.status_code}")
                return {}

            data = json.loads(response.text)
            print(data)
            return data
        except json.JSONDecodeError as e:
            self.log_info(f"JSON 解析失败: {e}")
            return {}
        except Exception as e:
            self.log_info(f"获取用电数据异常: {e}")
            return {}
    
    def _check_and_alert(self, data: dict) -> None:
        """检查余额并发送提醒
        
        Args:
            data: API 响应数据
        """
        try:
            # 验证响应
            if data.get('e') != 0 or data.get('d', {}).get('retcode') != 0:
                msg = data.get('d', {}).get('msg', '未知错误')
                self.log_info(f"查询失败: {msg}")
                return
            
            # 提取关键信息
            room_data = data.get('d', {})
            print(room_data)
            syje = float(room_data.get('syje', 0))  # 电费余额
            dffjbh = room_data.get('dffjbh', 'N/A')  # 宿舍编号
            room_name = room_data.get('roomName', 'N/A')  # 宿舍号
            
            self.log_info(f"宿舍: {room_name} ({dffjbh}) - 电费余额: {syje} 元")
            
            # 检查是否低于阈值
            if syje < self.threshold:
                subject = "【宿舍用电提醒】电费余额即将不足"
                content = f"""
亲爱的同学，您好：

您的宿舍用电信息如下：
- 宿舍号: {room_name}
- 宿舍编号: {dffjbh}
- 电费余额: {syje} 元

当前电费余额已低于 {self.threshold} 元，请及时充值，以免影响宿舍用电。

此为系统自动提醒邮件，请勿回复。
"""
                if self.send_email(subject, content):
                    self.log_success("电费余额提醒已发送")
                else:
                    self.log_info("电费余额提醒发送失败")
            else:
                self.log_info(f"电费余额充足 ({syje} >= {self.threshold})")

        except Exception as e:
            self.log_info(f"处理用电数据异常: {e}")
    
    def _should_send_daily_failure_alert(self) -> bool:
        """判断是否应该发送每日失败告警邮件

        条件：
        1. 今天还没有成功获取过数据
        2. 今天还没有发送过失败告警
        3. 当前时间已超过每日告警截止时间

        Returns:
            应该发送告警返回 True，否则返回 False
        """
        today = date.today()

        # 今天已有成功记录，无需告警
        if self._last_success_date == today:
            return False

        # 今天已经发送过告警
        if self._daily_failure_alert_sent_date == today:
            return False

        # 当前时间未到截止时间，暂不告警
        if datetime.now().hour < self._daily_alert_cutoff_hour:
            return False

        return True

    def _send_daily_failure_alert(self) -> None:
        """发送每日失败告警邮件（一天只发一次）"""
        subject = "【宿舍用电提醒】今日电费监控异常"
        content = f"""
亲爱的同学，您好：

今日宿舍用电监控系统未能成功获取电费数据，截至当前时间仍未成功。

可能原因为：
- 统一身份认证系统异常
- 网络连接问题
- 学校服务暂时不可用

请手动登录查看电费余额：https://online.uestc.edu.cn/site/bedroom

此为系统自动提醒邮件，请勿回复。
"""
        if self.send_email(subject, content):
            self.log_success("每日失败告警邮件已发送")
            self._daily_failure_alert_sent_date = date.today()

    def run(self) -> bool:
        """运行电费监控应用

        成功时更新上次成功日期；失败时检查是否需要发送每日失败告警。
        始终返回 True 以避免调度器层面发送额外的告警邮件。

        Returns:
            始终返回 True（告警逻辑已内部处理）
        """
        self.log_info("开始检查宿舍用电...")

        data = self._fetch_power_data()
        if not data:
            # 检查是否需要发送每日失败告警
            if self._should_send_daily_failure_alert():
                self._send_daily_failure_alert()
            # 返回 True 避免调度器输出 warning 进而触发额外告警邮件
            return True

        # 记录今日成功
        self._last_success_date = date.today()
        self._check_and_alert(data)
        return True
