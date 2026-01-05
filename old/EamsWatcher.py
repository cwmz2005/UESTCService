import os
# ====== 配置区 ======
# 账户信息（从环境变量读取）
USERNAME = os.getenv("EAMS_USERNAME", "")
PASSWORD = os.getenv("EAMS_PASSWORD", "")

# 邮件配置（从环境变量读取）
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASSWORD", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

# 文件路径
HISTORY_FILE = "sent_grades.json"

# API 端点
API_URL = "https://eamsapp.uestc.edu.cn/api/ydzc-app/grade/student"

# 时间配置
CHECK_INTERVAL_MINUTES = 30

# ===================

import json
import time
import urllib.parse
from typing import List, Set, Dict, Optional

import requests
import schedule
import yagmail

from UESTCAccount import UESTCAccount

# 尝试加载本地 .env 文件（如果存在）
if os.path.exists('.env'):
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"\'')
    except Exception as e:
        print(f"⚠️  警告：加载 .env 文件失败: {e}")

# 全局账户实例
account = None


def _validate_config() -> bool:
    """验证必要的配置信息是否已设置。
    
    Returns:
        所有配置都有效返回 True，否则返回 False
    """
    required_vars = {
        "EAMS_USERNAME": USERNAME,
        "EAMS_PASSWORD": PASSWORD,
        "EMAIL_USER": EMAIL_USER,
        "EMAIL_PASSWORD": EMAIL_PASS,
        "EMAIL_TO": EMAIL_TO,
    }
    
    missing_vars = [name for name, value in required_vars.items() if not value]
    
    if missing_vars:
        print(f"❌ 错误：以下环境变量未设置: {', '.join(missing_vars)}")
        print("\n请设置以下环境变量:")
        print("  - EAMS_USERNAME: EAMS 系统用户名")
        print("  - EAMS_PASSWORD: EAMS 系统密码")
        print("  - EMAIL_USER: 发件邮箱地址")
        print("  - EMAIL_PASSWORD: 邮箱授权码（非密码）")
        print("  - EMAIL_TO: 收件邮箱地址")
        print("\n你可以通过以下方式设置（Windows PowerShell）:")
        print("  $env:EAMS_USERNAME = 'your_username'")
        print("  $env:EAMS_PASSWORD = 'your_password'")
        print("  $env:EMAIL_USER = 'your_email@163.com'")
        print("  $env:EMAIL_PASSWORD = 'your_auth_code'")
        print("  $env:EMAIL_TO = 'recipient@example.com'")
        return False
    
    return True


def log(msg: str) -> None:
    """打印带时间戳的日志信息。
    
    Args:
        msg: 日志信息
    """
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def _get_bearer_token() -> Optional[str]:
    """获取用于 API 请求的 Bearer Token。
    
    通过访问认证 URL 并从重定向后的 URL 中提取 jsessionid。
    
    Returns:
        Bearer token 字符串，提取失败时返回 None
    """
    try:
        AUTH_URL = "https://idas.uestc.edu.cn/authserver/login?service=https%3A%2F%2Feamsapp.uestc.edu.cn%2Fapi%2Fblade-auth%2Fcas-login%3FredirectUrl%3Dhttps%3A%2F%2Feamsapp.uestc.edu.cn"
        if( not account):
            log("账户未登录，无法获取 bearer token")
            return None
        resp = account.session.get(
            AUTH_URL,
            allow_redirects=True,
            timeout=15
        )
        final_url = resp.url
        parsed = urllib.parse.urlparse(final_url)
        params = urllib.parse.parse_qs(parsed.query)
        
        jsessionid = None
        if 'jsessionid' in params:
            jsessionid = params['jsessionid'][0]
        elif 'jsessionid' in parsed.path:
            jsessionid = parsed.path.split('jsessionid=')[-1].split('&')[0]
        
        if jsessionid:
            return f"bearer {jsessionid}"
        else:
            log(f"未能在最终URL中提取jsessionid: {final_url}")
            return None
            
    except Exception as e:
        log(f"获取 bearer token 失败: {e}")
        return None


def fetch_grades() -> List[Dict]:
    """从 EAMS API 获取成绩数据。
    
    Returns:
        成绩数据列表，获取失败时返回空列表
    """
    blade_auth = _get_bearer_token()
    if not blade_auth:
        log("无法获取 blade-auth，跳过本次查询")
        return []
    
    headers = {"blade-auth": blade_auth}
    try:
        resp = requests.get(API_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") == 200 and data.get("success"):
            return data.get("data", [])
        else:
            log(f"API 返回异常: {data}")
            return []
            
    except Exception as e:
        log(f"请求成绩 API 失败: {e}")
        return []


def _load_sent_courses() -> Set[str]:
    """从历史文件中加载已发送的课程代码。
    
    Returns:
        已发送课程代码的集合
    """
    if not os.path.exists(HISTORY_FILE):
        return set()
    
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception as e:
        log(f"读取历史文件失败: {e}")
        return set()


def _save_sent_courses(course_codes: Set[str]) -> None:
    """保存已发送的课程代码到历史文件。
    
    Args:
        course_codes: 课程代码集合
    """
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(course_codes), f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"保存历史文件失败: {e}")


def _build_email_content(new_grades: List[Dict]) -> str:
    """生成邮件内容。
    
    Args:
        new_grades: 新成绩列表
        
    Returns:
        邮件内容字符串
    """
    lines = ["有新科目成绩已发布：\n"]
    for grade in new_grades:
        lines.append(
            f"课程名: {grade['courseName']}\n"
            f"成绩: {grade['score']}\n"
            f"学分: {grade['credits']}\n"
            f"课程类型: {grade['courseTypeName']}\n"
            f"学期: {grade['semester']}\n"
            f"教师: {grade.get('teacherName', '')}\n\n"
        )
    return "".join(lines)


def send_email(subject: str, content: str) -> None:
    """发送邮件通知。
    
    Args:
        subject: 邮件主题
        content: 邮件内容
    """
    try:
        yag = yagmail.SMTP(user=EMAIL_USER, password=EMAIL_PASS, host='smtp.163.com')
        yag.send(to=EMAIL_TO, subject=subject, contents=content)
        log("邮件已发送")
    except Exception as e:
        log(f"发送邮件失败: {e}")


def check_and_notify(retry: bool = True) -> None:
    """检查新成绩并发送邮件通知。
    
    获取最新成绩，与历史记录对比，若有新成绩则发送邮件。
    异常时先尝试重新登录一次，若成功则重试，若仍失败则报错。
    
    Args:
        retry: 是否在异常时重试登录（首次调用为 True，重试调用为 False 以防止无限循环）
    """
    try:
        log("开始检查成绩...")
        grades = fetch_grades()
        
        if not grades:
            log("未获取到成绩数据")
            import traceback
            err_detail = traceback.format_exc()
            send_email(
                "【EAMS成绩提醒】查询失败",
                f"未获取到成绩数据，可能是 API 或网络异常。\n\n错误详情：\n{err_detail}"
            )
            return
        
        sent_courses = _load_sent_courses()
        new_grades = [
            g for g in grades
            if g['courseCode'] not in sent_courses and g['status'] == '已发布'
        ]
        
        if new_grades:
            content = _build_email_content(new_grades)
            send_email("【EAMS成绩提醒】有新科目成绩已发布", content)
            sent_courses.update(g['courseCode'] for g in new_grades)
            _save_sent_courses(sent_courses)
            log(f"发现 {len(new_grades)} 个新成绩")
        else:
            log("无新成绩")
            
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        log(f"脚本运行异常: {e}")
        
        # 如果允许重试，先尝试重新登录一次
        if retry:
            log("尝试重新登录...")
            if not account:
                log("账户实例不存在，无法重新登录")
                return
            if account.login():
                log("重新登录成功，重试成绩检查...")
                check_and_notify(retry=False)  # 重试一次，但不再递归
                return
            else:
                log("重新登录失败，放弃重试")
        
        # 登录失败或已经重试过，发送错误邮件
        send_email(
            "【EAMS成绩提醒】脚本异常",
            f"脚本运行出错：{e}\n\n错误详情：\n{err_detail}"
        )


if __name__ == "__main__":
    # 验证配置
    if not _validate_config():
        exit(1)
    
    log("EAMS 成绩监控器启动")
    
    # 创建账户实例
    account = UESTCAccount(USERNAME, PASSWORD, log)
    
    # 登录
    if not account.login():
        log("登录失败，程序终止")
        exit(1)

    # 启动时先查一次
    check_and_notify()
    
    # 每 N 分钟查一次
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_and_notify)
    
    log(f"定时检查已启动，每 {CHECK_INTERVAL_MINUTES} 分钟检查一次")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(10)
    except KeyboardInterrupt:
        log("程序已停止")

