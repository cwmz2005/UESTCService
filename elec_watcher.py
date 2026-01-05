"""UESTC 宿舍用电监控应用"""

import json
from application import Application
from UESTCAccount import UESTCAccount


class ElecWatcherApp(Application):
    """宿舍用电监控应用，当电费余额低于阈值时发送邮件提醒"""
    
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
    
    def _refresh_session(self) -> bool:
        """刷新会话令牌
        
        Returns:
            刷新成功返回 True，失败返回 False
        """
        try:
            refresh_response = self.account.session.get(self.refresh_url)
            if refresh_response.status_code != 200:
                self.log_warning("会话刷新失败，尝试重新登录")
                if not self.account.login():
                    self.log_error("重新登录失败")
                    return False
            return True
        except Exception as e:
            self.log_error(f"刷新会话异常: {e}")
            return False
    
    def _fetch_power_data(self) -> dict:
        """获取宿舍用电数据
        
        Returns:
            包含电费数据的字典，获取失败返回空字典
        """
        try:
            if not self._refresh_session():
                return {}
            
            response = self.account.session.get(self.power_url, timeout=10)
            if response.status_code != 200:
                self.log_error(f"请求失败，状态码: {response.status_code}")
                return {}
            
            data = json.loads(response.text)
            return data
        except json.JSONDecodeError as e:
            self.log_error(f"JSON 解析失败: {e}")
            return {}
        except Exception as e:
            self.log_error(f"获取用电数据异常: {e}")
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
                self.log_warning(f"查询失败: {msg}")
                return
            
            # 提取关键信息
            room_data = data.get('d', {})
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
                    self.log_error("电费余额提醒发送失败")
            else:
                self.log_info(f"电费余额充足 ({syje} >= {self.threshold})")
        
        except Exception as e:
            self.log_error(f"处理用电数据异常: {e}")
    
    def run(self) -> bool:
        """运行电费监控应用
        
        Returns:
            运行成功返回 True，失败返回 False
        """
        self.log_info("开始检查宿舍用电...")
        
        data = self._fetch_power_data()
        if not data:
            return False
        
        self._check_and_alert(data)
        return True
