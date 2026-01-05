"""UESTC 定时服务系统架构说明

系统采用四层架构设计：

1. 账户层（Account Layer）
   └── UESTCAccount: 统一的账户管理和身份认证

2. 应用层（Application Layer）
   ├── Application: 应用基类
   ├── ElecWatcherApp: 宿舍用电监控
   ├── EamsWatcherApp: 成绩监控
   └── [可扩展] 其他应用模块

3. 操作层（Operation Layer）
   ├── Operation: 操作基类
   ├── EmailOperation: 邮件发送操作
   └── OperationManager: 操作管理器

4. 调度层（Scheduling Layer）
   ├── SchedulePolicy: 定时策略基类
   ├── IntervalPolicy: 间隔定时策略（每 N 秒执行一次）
   ├── CronPolicy: Cron 定时策略（每天指定时间执行）
   ├── ScheduledTask: 定时任务
   └── Scheduler: 任务调度器

5. 公共模块
   ├── Logger: 统一日志管理
   └── UESTCServiceSystem: 系统核心框架

系统特性：
- 所有模块共用一个 UESTCAccount 实例
- 所有模块共用一个 Logger 实例
- 所有模块通过 OperationManager 访问操作功能
- 支持灵活的定时策略（间隔模式、Cron 模式、自定义模式）
- 支持为每个应用单独配置不同的定时策略
- 支持同步和异步两种运行模式

快速开始：

1. 设置环境变量（Windows PowerShell）：
   $env:UESTC_USERNAME = '学号'
   $env:UESTC_PASSWORD = '密码'
   $env:EMAIL_USER = '邮箱@163.com'
   $env:EMAIL_PASSWORD = '授权码'
   $env:EMAIL_TO = '收件地址'

2. 运行系统：
   python main.py

3. 选择运行模式：
   - 同步模式：立即执行所有任务一次
   - 异步模式：启动定时调度器，后台持续运行

定时策略配置：

在 main.py 中配置各应用的定时策略：

```python
# 间隔定时策略（每 30 分钟执行一次）
system.set_app_schedule("ElecWatcher", IntervalPolicy(30 * 60))

# 间隔定时策略（每 2 小时执行一次）
system.set_app_schedule("EamsWatcher", IntervalPolicy(2 * 3600))

# Cron 定时策略（每天 8:30 执行）
system.set_app_schedule("MyApp", CronPolicy(8, 30))
```

添加新的应用模块：

1. 创建类继承 Application
2. 实现 run() 方法
3. 在 main.py 中注册该应用
4. 为应用设置定时策略

示例：创建新应用
```python
from application import Application

class MyApp(Application):
    def __init__(self, account):
        super().__init__("MyApp", account)
    
    def run(self) -> bool:
        self.log_info("运行我的应用")
        # 使用 self.account 进行操作
        # 使用 self.send_email() 发送邮件
        self.log_success("完成")
        return True
```

然后在 main.py 中注册：
```python
system.register_application(MyApp(system.account))
system.set_app_schedule("MyApp", IntervalPolicy(60 * 60))  # 每小时执行一次
```

文件结构：
├── UESTCAccount.py      # 账户层
├── logger.py            # 日志模块
├── operations.py        # 操作层
├── application.py       # 应用基类
├── scheduler.py         # 调度层
├── service_system.py    # 系统框架
├── elec_watcher.py      # 电费监控应用
├── eams_watcher.py      # 成绩监控应用
└── main.py              # 主入口
"""
