"""UESTC 定时服务系统 - 主入口
集中管理和运行所有应用模块
"""

import sys
import time
from service_system import UESTCServiceSystem
from elec_watcher import ElecWatcherApp
from eams_watcher import EamsWatcherApp
from scheduler import IntervalPolicy, CronPolicy


def main():
    """主程序入口"""
    try:
        # 第一层：账户层 + 操作层 + 日志模块
        print("=" * 60)
        print("UESTC 定时服务系统启动")
        print("=" * 60)
        
        system = UESTCServiceSystem.from_environment()
        
        # 第二层：应用层 - 注册应用模块
        print("\n注册应用模块...")
        system.register_application(ElecWatcherApp(system.account, threshold=10.0))
        system.register_application(EamsWatcherApp(system.account))
        
        # 配置各应用的定时策略
        print("\n配置定时策略...")
        # ElecWatcher：每 30 分钟检查一次电费
        system.set_app_schedule("ElecWatcher", IntervalPolicy(30 * 60))
        # EamsWatcher：每 1 小时检查一次成绩
        system.set_app_schedule("EamsWatcher", IntervalPolicy(1 * 3600))
        
        # 第一步：账户登录
        print("\n执行账户认证...")
        if not system.login():
            print("❌ 账户登录失败，退出程序")
            return 1
        
        # 第二步：立即执行一次所有应用
        print("\n" + "=" * 60)
        print("初始化：立即执行一次所有应用...")
        print("=" * 60)
        success_count = system.run_all_applications()
        
        # 第三步：启动定时调度器（异步模式）
        print("\n" + "=" * 60)
        print("启动定时调度器（异步模式）...")
        print("定时策略:")
        for app_name, policy in system.app_schedules.items():
            print(f"  - {app_name}: {policy.get_description()}")
        
        # 启动调度器
        system.start_scheduler(check_interval=30)  # 每 30 秒检查一次
        
        print("\n调度器已启动，按 Ctrl+C 停止程序...")
        print("=" * 60)
        
        try:
            # 保持主线程运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n收到停止信号，正在关闭调度器...")
            system.stop_scheduler()
            print("调度器已关闭")
        
        return 0
        print(f"❌ 配置错误: {e}")
        print("\n请设置以下环境变量:")
        print("  - UESTC_USERNAME: UESTC 学号")
        print("  - UESTC_PASSWORD: UESTC 密码")
        print("  - EMAIL_USER: 发件邮箱（163邮箱）")
        print("  - EMAIL_PASSWORD: 邮箱授权码")
        print("  - EMAIL_TO: 收件邮箱地址")
        return 1
    
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
