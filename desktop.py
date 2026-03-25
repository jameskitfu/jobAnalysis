"""
技能词频统计工具 - 桌面版入口
启动 Flask 服务后自动打开系统默认浏览器
"""

import threading
import socket
import time
import webbrowser
import signal
import sys
from app import start_server


def find_free_port():
    """获取一个可用的空闲端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def main():
    """桌面应用主入口"""
    port = find_free_port()
    url = f'http://127.0.0.1:{port}'

    print("=" * 50)
    print("技能词频统计工具 v1.2.0 (桌面版)")
    print(f"服务地址：{url}")
    print("关闭此窗口即可退出服务")
    print("=" * 50)

    # 在后台线程启动 Flask
    server_thread = threading.Thread(
        target=start_server,
        args=(port,),
        daemon=True
    )
    server_thread.start()

    # 等待 Flask 启动就绪
    for _ in range(30):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=1):
                break
        except OSError:
            time.sleep(0.2)

    # 自动打开默认浏览器
    webbrowser.open(url)

    # 保持主进程存活（Ctrl+C 或关闭窗口退出）
    try:
        signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n服务已关闭。")


if __name__ == '__main__':
    main()
