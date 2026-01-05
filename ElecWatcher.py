import os
import json
from dotenv import load_dotenv
from UESTCAccount import UESTCAccount
import yagmail

# 加载环境变量
load_dotenv()

# 邮件配置（从环境变量读取）
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASSWORD", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

# 全局账户实例
account = None
def send_email(subject: str, content: str) -> None:
    """发送邮件通知。
    
    Args:
        subject: 邮件主题
        content: 邮件内容
    """
    try:
        yag = yagmail.SMTP(user=EMAIL_USER, password=EMAIL_PASS, host='smtp.163.com')
        yag.send(to=EMAIL_TO, subject=subject, contents=content)
        print("邮件已发送")
    except Exception as e:
        print(f"发送邮件失败: {e}")


def getPowerData():
    POWER_URL = "https://online.uestc.edu.cn/site/bedroom"
    if account is None:
        raise RuntimeError("账户未初始化")
    refreshSubsiteToken = account.session.get(r"https://idas.uestc.edu.cn/authserver/login?service=https%3A%2F%2Fonline.uestc.edu.cn%2Fcommon%2FactionCasLogin%3Fredirect_url%3Dhttps%253A%252F%252Fonline.uestc.edu.cn%252Fpage%252F")
    if(refreshSubsiteToken.status_code != 200):
        if(account.login()):
            getPowerData()
        return
    r = account.session.get(POWER_URL)
    
    try:
        # 解析 JSON 响应
        data = json.loads(r.text)
        
        # 检查响应状态
        if data.get('e') != 0 or data.get('d', {}).get('retcode') != 0:
            print(f"查询失败: {data.get('d', {}).get('msg', '未知错误')}")
            return
        
        # 提取电费余额和宿舍编号
        syje = float(data.get('d', {}).get('syje', 0))  # 宿舍电费余额
        dffjbh = data.get('d', {}).get('dffjbh', '')    # 宿舍唯一编号
        room_name = data.get('d', {}).get('roomName', '')
        
        print(f"宿舍: {room_name} ({dffjbh}) - 电费余额: {syje} 元")
        
        # 当电费余额低于 10 元时发送邮件
        if syje < 1000:
            subject = "【宿舍用电提醒】电费余额即将不足"
            content = f"""
亲爱的同学，您好：

您的宿舍用电信息如下：
- 宿舍号: {room_name}
- 宿舍编号: {dffjbh}
- 电费余额: {syje} 元

当前电费余额已低于 10 元，请及时充值，以免影响宿舍用电。

此为系统自动提醒邮件，请勿回复。
"""
            send_email(subject, content)
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        print(f"响应内容: {r.text}")
    except Exception as e:
        print(f"处理响应异常: {e}")

if __name__ == "__main__":
    USERNAME = os.getenv('USERNAME', '')
    PW = os.getenv('PASSWORD', '')
    
    if not USERNAME or not PW:
        raise RuntimeError("请设置环境变量 UESTC_USERNAME 和 UESTC_PASSWORD")
    
    if not EMAIL_USER or not EMAIL_PASS or not EMAIL_TO:
        raise RuntimeError("请设置邮件环境变量: EMAIL_USER, EMAIL_PASSWORD, EMAIL_TO")
    
    # 创建账户实例
    account = UESTCAccount(USERNAME, PW)
    
    if account.login():
        print("登录成功")
        getPowerData()
    else:
        print("登录失败")
        getPowerData()