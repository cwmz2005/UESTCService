# UESTC 定时服务系统

一个功能完整的 UESTC 学生服务监控系统，支持成绩监控、宿舍用电监控等功能，具有灵活的定时策略和邮件告警机制。

## 📋 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [使用指南](#使用指南)
- [模块说明](#模块说明)
- [部署指南](#部署指南)
- [故障排查](#故障排查)

## ✨ 功能特性

### 核心功能

- 🎓 **EAMS 成绩监控** - 实时监控成绩发布，新成绩自动邮件通知
- 💡 **宿舍用电监控** - 定时检查电费余额，余额不足自动告警
- 📧 **邮件通知系统** - 多种通知方式，包括成绩通知、电费提醒、系统告警
- 🕐 **灵活定时策略** - 支持间隔定时和 Cron 定时，每个模块独立配置
- 📝 **完整日志系统** - 控制台实时输出 + 按日期文件保存 + 错误告警
- 🔄 **后台异步运行** - 使用 Systemd 服务，24/7 持续监控
- 🔌 **易于扩展** - 模块化设计，支持快速添加新的应用和操作

### 系统特性

- 共享账户实例 - 所有模块使用同一个登录会话
- 统一日志管理 - 所有模块使用同一个日志实例
- 集中操作管理 - 通过 OperationManager 统一调度
- 灵活的错误处理 - 错误和警告自动发送邮件告警
- 无缓冲日志输出 - 实时看到系统运行状态

## 🏗️ 系统架构

采用四层分层架构设计：

```
┌─────────────────────────────────────┐
│     应用层 (Application Layer)      │
├─────────────────────────────────────┤
│ ElecWatcherApp  │  EamsWatcherApp  │
│                 │  (可扩展其他应用)  │
├─────────────────────────────────────┤
│     操作层 (Operation Layer)        │
├─────────────────────────────────────┤
│     EmailOperation + 邮件管理        │
├─────────────────────────────────────┤
│    调度层 (Scheduling Layer)        │
├─────────────────────────────────────┤
│ IntervalPolicy │ CronPolicy │ 自定义 │
├─────────────────────────────────────┤
│  账户层 (Account Layer) + 日志模块   │
├─────────────────────────────────────┤
│ UESTCAccount (共享) + Logger (共享) │
└─────────────────────────────────────┘
```

### 各层职责

| 层级 | 组件 | 职责 |
|------|------|------|
| 账户层 | UESTCAccount | 统一账户管理和身份认证 |
| 日志层 | Logger | 日志打印、文件保存、告警邮件 |
| 应用层 | Application | 各业务模块的基类 |
| 操作层 | Operation | 邮件发送等通用操作 |
| 调度层 | Scheduler | 定时任务管理和调度 |
| 框架层 | UESTCServiceSystem | 系统核心框架，协调各层 |

## 🚀 快速开始

### 系统要求

- Python 3.8 或更高版本
- pip 包管理器
- 网络连接（用于登录和邮件发送）

### Windows 本地开发

#### 1. 克隆项目

```bash
git clone <项目地址>
cd UESTCService
```

#### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Windows CMD:
venv\Scripts\activate.bat

# Linux/Mac:
source venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 配置环境变量

创建 `.env` 文件：

```bash
# 编辑 .env 文件
# Linux/Mac:
nano .env

# Windows (使用记事本或 VS Code)
type nul > .env
```

填充以下内容：

```env
# UESTC 账户配置
UESTC_USERNAME=你的学号
UESTC_PASSWORD=你的密码

# 邮件配置（推荐使用 163 邮箱）
EMAIL_USER=你的163邮箱@163.com
EMAIL_PASSWORD=邮箱授权码
EMAIL_TO=接收邮件地址
```

> 📌 获取 163 邮箱授权码：
> 1. 登录 163 邮箱
> 2. 进入设置 → POP3/SMTP/IMAP
> 3. 开启 SMTP 服务，获取授权码

#### 5. 运行系统

```bash
# 无缓冲模式运行（推荐）
python -u main.py

# 或直接运行
python main.py
```

系统将：
1. 初始化系统并登录
2. 立即执行一次所有应用
3. 启动后台定时调度器
4. 按配置的策略定时执行各应用

## ⚙️ 配置说明

### 环境变量配置

在 `.env` 文件中配置（必需）：

| 变量 | 说明 | 示例 |
|------|------|------|
| UESTC_USERNAME | UESTC 学号 | 2024000001 |
| UESTC_PASSWORD | UESTC 密码 | mypassword |
| EMAIL_USER | 发件邮箱 | myemail@163.com |
| EMAIL_PASSWORD | 邮箱授权码 | abcdefgh1234 |
| EMAIL_TO | 收件邮箱 | receiver@example.com |

### 定时策略配置

在 `main.py` 中修改各应用的定时策略：

```python
# 间隔定时（每 N 秒执行一次）
system.set_app_schedule("ElecWatcher", IntervalPolicy(30 * 60))  # 每 30 分钟

# Cron 定时（每天指定时间执行）
system.set_app_schedule("EamsWatcher", CronPolicy(8, 30))  # 每天 8:30
```

## 📖 使用指南

### 同步运行（测试）

在主线程中立即执行所有应用一次：

```bash
# 修改 main.py，注释掉异步模式代码，调用：
system.run_all_applications()
```

### 异步运行（生产）

启动后台定时调度器：

```bash
python -u main.py

# 按 Ctrl+C 停止程序
```

### 查看日志

```bash
# 控制台实时日志
# 程序运行时自动输出

# 查看日志文件
cat log/2026-01-05.log          # Linux/Mac
type log\2026-01-05.log         # Windows

# 最新的日志内容
tail -f log/$(date +%Y-%m-%d).log  # Linux/Mac
```

### 添加新的应用模块

#### 第 1 步：创建应用类

创建 `my_app.py`：

```python
from application import Application
from UESTCAccount import UESTCAccount

class MyApp(Application):
    """我的自定义应用"""
    
    def __init__(self, account: UESTCAccount):
        super().__init__("MyApp", account)
    
    def run(self) -> bool:
        """运行应用"""
        self.log_info("开始执行我的应用...")
        
        try:
            # 使用 self.account 访问登录会话
            response = self.account.session.get("https://example.com")
            
            # 使用 self.send_email() 发送邮件
            if some_condition:
                self.send_email("标题", "内容")
            
            self.log_success("应用执行成功")
            return True
        except Exception as e:
            self.log_error(f"应用执行失败: {e}")
            return False
```

#### 第 2 步：在 main.py 中注册

```python
from my_app import MyApp

# 在 main() 函数中
system.register_application(MyApp(system.account))

# 配置定时策略
system.set_app_schedule("MyApp", IntervalPolicy(3600))  # 每小时执行一次
```

#### 第 3 步：运行

```bash
python -u main.py
```

## 📁 模块说明

### 核心模块

| 文件 | 说明 | 功能 |
|------|------|------|
| `main.py` | 主入口 | 系统初始化、应用注册、定时配置 |
| `service_system.py` | 系统框架 | 协调各层，管理应用和调度器 |
| `application.py` | 应用基类 | 所有应用的基类，提供通用方法 |
| `logger.py` | 日志管理 | 统一日志输出、文件保存、告警邮件 |
| `operations.py` | 操作层 | 邮件操作及操作管理器 |
| `scheduler.py` | 调度层 | 定时策略和任务调度器 |
| `UESTCAccount.py` | 账户管理 | UESTC 账户登录和会话管理 |

### 应用模块

| 文件 | 说明 | 功能 |
|------|------|------|
| `eams_watcher.py` | 成绩监控应用 | 监控 EAMS 成绩发布 |
| `elec_watcher.py` | 用电监控应用 | 监控宿舍用电余额 |

## 🚢 部署指南

### Ubuntu 服务器部署

#### 1. 环境准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 和 pip
sudo apt install -y python3 python3-pip python3-venv git
```

#### 2. 部署项目

```bash
# 创建项目目录
sudo mkdir -p /opt/uestc-service
cd /opt/uestc-service

# 克隆项目
sudo git clone <项目地址> .

# 创建虚拟环境
sudo python3 -m venv venv

# 安装依赖
sudo bash -c 'source venv/bin/activate && pip install -r requirements.txt'

# 设置权限
sudo chown -R $USER:$USER /opt/uestc-service
```

#### 3. 配置环境变量

```bash
# 创建 .env 文件
nano /opt/uestc-service/.env

# 添加配置内容（同上）
# 保存：Ctrl + O → Enter → Ctrl + X

# 设置权限（只有所有者可读）
chmod 600 /opt/uestc-service/.env
```

#### 4. 创建 Systemd 服务

```bash
# 创建服务文件
sudo nano /etc/systemd/system/uestc-service.service
```

填充以下内容：

```ini
[Unit]
Description=UESTC Timing Service System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/uestc-service
Environment="PATH=/opt/uestc-service/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/uestc-service/venv/bin/python3 /opt/uestc-service/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 5. 启用并启动服务

```bash
# 刷新 systemd 配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable uestc-service

# 启动服务
sudo systemctl start uestc-service

# 查看服务状态
sudo systemctl status uestc-service

# 查看实时日志
sudo journalctl -u uestc-service -f
```

#### 6. 日志轮转配置

```bash
# 创建日志轮转规则
sudo nano /etc/logrotate.d/uestc-service
```

填充以下内容：

```
/opt/uestc-service/log/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 root root
}
```

### 服务管理命令

```bash
# 启动服务
sudo systemctl start uestc-service

# 停止服务
sudo systemctl stop uestc-service

# 重启服务
sudo systemctl restart uestc-service

# 查看服务状态
sudo systemctl status uestc-service

# 查看实时日志
sudo journalctl -u uestc-service -f

# 查看最近 100 行日志
sudo journalctl -u uestc-service -n 100

# 禁用开机自启
sudo systemctl disable uestc-service
```

## 🔧 故障排查

### 问题 1：导入模块失败

```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案：**

```bash
# 确保虚拟环境已激活
source venv/bin/activate  # Linux/Mac
venv\Scripts\Activate.ps1  # Windows PowerShell

# 重新安装依赖
pip install -r requirements.txt
```

### 问题 2：登录失败

```
错误：账户登录失败
```

**检查清单：**

1. 确认 UESTC 用户名和密码正确
2. 检查网络连接
3. 查看 `log/` 文件夹中的日志文件
4. 确认 UESTC 统一身份认证服务在线

### 问题 3：邮件发送失败

```
错误：发送邮件失败
```

**检查清单：**

1. 确认邮箱地址格式正确
2. 确认邮箱授权码正确（不是密码）
3. 确认 SMTP 服务已开启
4. 检查网络连接
5. 查看日志文件获取详细错误信息

### 问题 4：定时任务不执行

**检查清单：**

```bash
# 查看任务调度器日志
tail -f log/$(date +%Y-%m-%d).log

# 验证调度器是否启动
sudo systemctl status uestc-service

# 查看 systemd 日志
sudo journalctl -u uestc-service
```

### 问题 5：日志输出延迟

**解决方案：**

确保使用无缓冲模式运行：

```bash
# Windows/Linux
python -u main.py

# 或在服务文件中添加
Environment="PYTHONUNBUFFERED=1"
```

## 📊 日志文件结构

```
log/
├── 2026-01-05.log
├── 2026-01-06.log
├── 2026-01-07.log
└── ...
```

日志格式示例：

```
[2026-01-05 14:30:45] [INFO] [UESTCServiceSystem] 服务系统初始化完成
[2026-01-05 14:30:46] [SUCCESS] [UESTCServiceSystem] 账户登录成功
[2026-01-05 14:30:47] [INFO] [ElecWatcher] 开始检查宿舍用电...
[2026-01-05 14:30:50] [SUCCESS] [ElecWatcher] 宿舍: 122128 (122128) - 电费余额: 150.45 元
[2026-01-05 14:30:51] [INFO] [EamsWatcher] 开始检查成绩...
[2026-01-05 14:30:55] [SUCCESS] [EamsWatcher] 暂无新成绩
```

## 📧 邮件通知类型

### 1. 成绩发布通知

**触发条件：** 检测到新成绩  
**收件人：** EMAIL_TO  
**内容：** 新发布的课程成绩和 GPA

### 2. 电费余额提醒

**触发条件：** 电费余额 < 10 元  
**收件人：** EMAIL_TO  
**内容：** 当前余额、宿舍号、充值提示

### 3. 系统错误告警

**触发条件：** 应用执行出错  
**收件人：** EMAIL_TO  
**内容：** 错误信息、发生时间、堆栈跟踪

### 4. 系统警告告警

**触发条件：** 出现警告日志  
**收件人：** EMAIL_TO  
**内容：** 警告信息、发生时间

## 🔐 安全建议

1. **保护 .env 文件** - 不要将 .env 提交到 Git
2. **使用邮箱授权码** - 不要在 .env 中存储邮箱密码
3. **权限管理** - 在 Ubuntu 上限制 .env 文件权限为 600
4. **日志管理** - 定期清理日志文件，防止磁盘满

## 📝 开发指南

### 项目结构

```
UESTCService/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py                  # 主入口
├── service_system.py        # 系统框架
├── application.py           # 应用基类
├── logger.py                # 日志管理
├── operations.py            # 操作层
├── scheduler.py             # 调度层
├── UESTCAccount.py          # 账户管理
├── eams_watcher.py          # 成绩监控应用
├── elec_watcher.py          # 用电监控应用
├── log/                     # 日志文件夹（自动创建）
│   ├── 2026-01-05.log
│   └── ...
└── venv/                    # 虚拟环境
```

### 代码规范

- 使用 Python 3.8+ 特性
- 遵循 PEP 8 风格指南
- 所有公开方法都有文档字符串
- 使用类型提示

### 扩展应用

参考 `eams_watcher.py` 和 `elec_watcher.py` 创建新的应用模块。

## 🐛 报告问题

遇到问题时，请：

1. 检查日志文件 (`log/` 文件夹)
2. 查看 systemd 日志 (Ubuntu): `sudo journalctl -u uestc-service`
3. 在控制台运行测试确认环境配置
4. 提供详细的错误信息和日志

## 📄 许可证

MIT License

## 👨‍💻 贡献

欢迎提交 Issue 和 Pull Request！

## ❓ 常见问题

**Q: 系统在后台运行时会占用很多资源吗？**

A: 不会。系统只在定时任务执行时才会进行网络请求和处理，其余时间处于睡眠状态，占用资源很小。

**Q: 可以同时运行多个应用吗？**

A: 可以。所有应用共享同一个账户会话，节省登录成本。

**Q: 邮件发送失败会影响系统运行吗？**

A: 不会。邮件发送失败只会记录到日志中，不会中断主程序。

**Q: 如何修改定时时间？**

A: 修改 `main.py` 中的 `set_app_schedule()` 调用，重启服务即可。

**Q: 日志文件会无限增长吗？**

A: 不会。系统每天生成一个新的日志文件，可配置日志轮转自动删除旧文件。

---

**需要帮助？** 查看日志文件或参考本 README 的相关部分。
