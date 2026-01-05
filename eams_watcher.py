"""UESTC 成绩监控应用"""

import json
import urllib.parse
from typing import List, Set, Dict, Optional
from application import Application
from UESTCAccount import UESTCAccount


class EamsWatcherApp(Application):
    """EAMS 成绩监控应用，当有新成绩发布时发送邮件提醒"""
    
    API_URL = "https://eamsapp.uestc.edu.cn/api/ydzc-app/grade/student"
    HISTORY_FILE = "sent_grades.json"
    
    def __init__(self, account: UESTCAccount, history_file: Optional[str] = None):
        """初始化成绩监控应用
        
        Args:
            account: 共享的 UESTCAccount 实例
            history_file: 历史记录文件路径（可选）
        """
        super().__init__("EamsWatcher", account)
        self.history_file = history_file or self.HISTORY_FILE
        self.sent_courses: Set[str] = self._load_sent_courses()
    
    def _get_bearer_token(self) -> Optional[str]:
        """获取 EAMS API 的 Bearer Token
        
        Returns:
            Bearer token 字符串，获取失败返回 None
        """
        try:
            auth_url = "https://idas.uestc.edu.cn/authserver/login?service=https%3A%2F%2Feamsapp.uestc.edu.cn%2Fapi%2Fblade-auth%2Fcas-login%3FredirectUrl%3Dhttps%3A%2F%2Feamsapp.uestc.edu.cn"
            
            resp = self.account.session.get(auth_url, allow_redirects=True, timeout=15)
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
                self.log_warning(f"未能在最终URL中提取jsessionid: {final_url}")
                return None
        
        except Exception as e:
            self.log_error(f"获取 bearer token 失败: {e}")
            return None
    
    def _fetch_grades(self) -> List[Dict]:
        """从 EAMS API 获取成绩数据
        
        Returns:
            成绩数据列表，获取失败返回空列表
        """
        blade_auth = self._get_bearer_token()
        if not blade_auth:
            self.log_warning("无法获取 blade-auth，跳过本次查询")
            return []
        
        headers = {"blade-auth": blade_auth}
        try:
            resp = self.account.session.get(self.API_URL, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") == 200 and data.get("success"):
                return data.get("data", [])
            else:
                self.log_warning(f"API 返回异常: {data}")
                return []
        
        except Exception as e:
            self.log_error(f"请求成绩 API 失败: {e}")
            return []
    
    def _load_sent_courses(self) -> Set[str]:
        """从历史文件中加载已发送的课程代码
        
        Returns:
            已发送课程代码的集合
        """
        import os
        if not os.path.exists(self.history_file):
            return set()
        
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            self.log_warning(f"读取历史文件失败: {e}")
            return set()
    
    def _save_sent_courses(self) -> None:
        """保存已发送的课程代码到历史文件"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(list(self.sent_courses), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_error(f"保存历史文件失败: {e}")
    
    def _build_email_content(self, new_grades: List[Dict]) -> str:
        """生成邮件内容
        
        Args:
            new_grades: 新成绩列表
            
        Returns:
            邮件内容字符串
        """
        lines = ["有新科目成绩已发布：\n"]
        for grade in new_grades:
            course_name = grade.get("courseName", "未知课程")
            score = grade.get("score", "未出分")
            gpa = grade.get("gpa", "N/A")
            lines.append(f"- {course_name}: {score} (GPA: {gpa})")
        
        lines.append("\n此为系统自动提醒邮件，请勿回复。")
        return "\n".join(lines)
    
    def run(self) -> bool:
        """运行成绩监控应用
        
        Returns:
            运行成功返回 True，失败返回 False
        """
        self.log_info("开始检查成绩...")
        
        grades = self._fetch_grades()
        if not grades:
            self.log_warning("未获取到成绩数据")
            return False
        
        # 识别新成绩
        new_grades = []
        for grade in grades:
            course_code = grade.get("courseName", "")
            if course_code and course_code not in self.sent_courses:
                new_grades.append(grade)
                self.sent_courses.add(course_code)
        
        if new_grades:
            self.log_info(f"发现 {len(new_grades)} 个新成绩")
            subject = "【EAMS成绩提醒】有新科目成绩已发布"
            content = self._build_email_content(new_grades)
            
            if self.send_email(subject, content):
                self._save_sent_courses()
                self.log_success("成绩提醒已发送")
                return True
            else:
                self.log_error("成绩提醒发送失败")
                # 发送失败时不更新历史记录，下次重试
                self.sent_courses = self._load_sent_courses()
                return False
        else:
            self.log_info("暂无新成绩")
            return True
