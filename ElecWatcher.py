import requests
import base64
import random
import os
from dotenv import load_dotenv
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from bs4 import BeautifulSoup

# 加载环境变量
load_dotenv()

s = requests.Session()
# 对应 JS 中的 $aes_chars
AES_CHARS = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"
headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        #"Host": "idas.uestc.edu.cn",   //HOST不对过不了！不需要HOST头
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
def random_string(length):
    """还原 JS 的 randomString 函数"""
    return ''.join(random.choice(AES_CHARS) for _ in range(length))

def encrypt_password(password, salt):
    """
    还原 JS 的 encryptPassword 逻辑
    :param password: 你的明文密码
    :param salt: 页面上提取到的加密盐 (pwdDefaultEncryptSalt)
    """
    if not salt:
        return password
    
    # 1. 模拟 JS 的准备工作
    # encryptAES(randomString(64) + password, salt, randomString(16))
    prefix_random = random_string(64)
    text_to_encrypt = prefix_random + password
    iv_random = random_string(16)
    
    # 2. 设置 AES 参数
    key = salt.strip().encode('utf-8')
    iv = iv_random.encode('utf-8')
    
    # 3. 执行 AES CBC Pkcs7 加密
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(text_to_encrypt.encode('utf-8'), AES.block_size, style='pkcs7')
    encrypted_bytes = cipher.encrypt(padded_data)
    
    # 4. 返回 Base64 编码后的字符串
    return base64.b64encode(encrypted_bytes).decode('utf-8')

def login() -> bool:
    USERNAME = os.getenv('UESTC_USERNAME', '')
    PW = os.getenv('UESTC_PASSWORD', '')
    
    if not USERNAME or not PW:
        raise RuntimeError("请设置环境变量 UESTC_USERNAME 和 UESTC_PASSWORD")
    
    URL = os.getenv('LOGIN_URL', r"https://idas.uestc.edu.cn/authserver/login?service=https%3A%2F%2Fonline.uestc.edu.cn%2Fcommon%2FactionCasLogin%3Fredirect_url%3Dhttps%253A%252F%252Fonline.uestc.edu.cn%252Fpage%252F")
    CAPCHECK_URL = os.getenv('CAPCHECK_URL', r"https://idas.uestc.edu.cn/authserver/checkNeedCaptcha.htl?username=") + USERNAME
    FINGERPRINT_URL = os.getenv('FINGERPRINT_URL', r"https://idas.uestc.edu.cn/authserver/bfp/info?bfp=1AEE9A6A77D6CAA491AFA55B9EF54C34&_=1767240745832")
    #获取execution串，salt
    s.headers.update(headers)
    res = s.get(URL)
    resSoup = BeautifulSoup(res.text,'lxml')
    exe = resSoup.find(id='execution')
    salt = resSoup.find('input',attrs={'id':'pwdEncryptSalt'})
    if(not salt):
        raise RuntimeError("获取salt失败")
    PW_SALT = salt['value']
    #PW_SALT = "1J5lGx9MRfdkURBX"
    #加密密码
    enc_password = encrypt_password(PW,PW_SALT)
    print("加密后密码:",enc_password)
    if(not exe):
        raise RuntimeError("获取execution失败")
    execution = exe['value']
    c = s.get(CAPCHECK_URL)
    print("是否需要验证码:",c.text)
    payload = {
        "username": USERNAME,
        "password": enc_password,
        "captcha": "",
        "rememberMe": "true",
        "_eventId": "submit",
        "cllt": "userNameLogin",
        "dllt": "generalLogin",
        "lt": "",
        "execution": execution
    }   #调了这么久，居然是URL编码的问题...
    s.get(FINGERPRINT_URL)
    #org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE=zh_CN
    s.cookies.update({'org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE':'zh_CN'})
    # print(s.cookies)
    p = s.post(URL,data=payload,allow_redirects=True)
    p = s.get(URL)
    #print(s.cookies.get_dict())
    # with open("result.html","w",encoding='utf-8') as f:
    #     f.write(p.text)
    if(p.status_code==200 and "统一身份认证" not in p.text):
        return True
    print("登录响应状态码:",p.status_code)
    print("登录响应内容:",p.text)
    print(s.cookies.get_dict())
    print(p.history)
    return False
def getPowerData():
    POWER_URL = "https://online.uestc.edu.cn/site/bedroom"
    r = s.get(POWER_URL)
    print(r.text)
if __name__ == "__main__":
    if(login()):
        print("登录成功")
        getPowerData()
    else:
        print("登录失败")
        getPowerData()