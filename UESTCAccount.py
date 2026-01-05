import base64
import random
import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


class UESTCAccount:
    """UESTC 学生账户管理类，负责身份认证和会话管理。"""
    
    # 登录相关 URL
    LOGIN_URL = "https://idas.uestc.edu.cn/authserver/login"
    
    # 验证码检查 URL
    CAPCHECK_URL = "https://idas.uestc.edu.cn/authserver/checkNeedCaptcha.htl?username="
    
    # 指纹信息 URL
    FINGERPRINT_URL = "https://idas.uestc.edu.cn/authserver/bfp/info?bfp=1AEE9A6A77D6CAA491AFA55B9EF54C34"
    
    # HTTP Headers 配置
    DEFAULT_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Pragma": "no-cache",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"'
    }
    
    # AES 加密字符集
    AES_CHARS = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"
    
    def __init__(self, username: str, password: str, log_func=None):
        """初始化 UESTC 账户。
        
        Args:
            username: 用户名
            password: 密码
            log_func: 日志函数，默认为 print
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.log = log_func or print
    
    def _random_string(self, length: int) -> str:
        """生成指定长度的随机字符串，用于 AES 加密前缀和 IV。
        
        Args:
            length: 字符串长度
            
        Returns:
            随机字符串
        """
        return ''.join(random.choice(self.AES_CHARS) for _ in range(length))
    
    def _encrypt_password(self, password: str, salt: str) -> str:
        """使用 AES CBC 加密密码。
        
        模仿 JavaScript 前端的加密逻辑，对密码进行 AES-128-CBC 加密。
        
        Args:
            password: 明文密码
            salt: 加密盐值
            
        Returns:
            Base64 编码的加密密码
        """
        if not salt:
            return password
        
        # 生成随机前缀和 IV
        prefix_random = self._random_string(64)
        text_to_encrypt = prefix_random + password
        iv_random = self._random_string(16)
        
        # 设置 AES 参数
        key = salt.strip().encode('utf-8')
        iv = iv_random.encode('utf-8')
        
        # 执行 AES CBC Pkcs7 加密
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_data = pad(text_to_encrypt.encode('utf-8'), AES.block_size, style='pkcs7')
        encrypted_bytes = cipher.encrypt(padded_data)
        
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    
    def login(self) -> bool:
        """登录到 EAMS 系统。
        
        获取登录页面的 salt 值，加密密码，然后提交登录表单。
        
        Returns:
            登录成功返回 True，失败返回 False
        """
        try:
            self.session.headers.update(self.DEFAULT_HEADERS)
            
            # 获取登录页面，提取 execution 和 salt
            login_response = self.session.get(self.LOGIN_URL)
            soup = BeautifulSoup(login_response.text, 'lxml')
            
            execution_element = soup.find(id='execution')
            salt_element = soup.find('input', attrs={'id': 'pwdEncryptSalt'})
            
            if not salt_element:
                self.log("获取 salt 失败")
                return False
            
            if not execution_element:
                self.log("获取 execution 失败")
                return False
            
            salt_value = salt_element['value']
            execution = execution_element['value']
            
            # 加密密码
            encrypted_password = self._encrypt_password(self.password, str(salt_value))
            self.log(f"密码已加密")
            
            # 检查是否需要验证码
            capcheck_response = self.session.get(self.CAPCHECK_URL + self.username)
            self.log(f"验证码检查: {capcheck_response.text}")
            
            # 准备登录请求
            payload = {
                "username": self.username,
                "password": encrypted_password,
                "captcha": "",
                "rememberMe": "true",
                "_eventId": "submit",
                "cllt": "userNameLogin",
                "dllt": "generalLogin",
                "lt": "",
                "execution": execution
            }
            
            # 获取指纹信息
            self.session.get(self.FINGERPRINT_URL)
            
            # 更新 Cookie
            self.session.cookies.update({'org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE': 'zh_CN'})
            
            # 提交登录请求
            login_response = self.session.post(self.LOGIN_URL, data=payload)
            
            if login_response.status_code == 200 and "统一身份认证" not in login_response.text:
                self.log("登录成功")
                return True
            
            self.log(f"登录失败 - 状态码: {login_response.status_code}")
            return False
            
        except Exception as e:
            self.log(f"登录异常: {e}")
            return False