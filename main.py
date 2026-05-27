"""
等保测评进度管理系统 - 程序入口
等保测评进度管理系统的启动脚本，负责初始化运行环境并启动GUI主窗口

一个基于Python Tkinter的桌面端看板应用，用于管理
等保测评项目的进度跟踪和流程管理。

运行方式：
    python main.py

打包方式（生成EXE）：
    pyinstaller --onefile --windowed --name "等保测评进度管理系统" main.py
"""

import sys  # 导入系统模块，用于修改Python模块搜索路径
import os    # 导入操作系统模块，用于获取文件路径信息

# 将项目根目录加入Python路径，确保模块导入正常
# sys.path.insert 在路径列表头部插入当前脚本所在目录，使得后续import能正确找到项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow  # 导入主窗口类，应用程序的顶层GUI窗口


def main():
    """应用程序主入口函数
    创建MainWindow实例（继承tk.Tk），并启动Tkinter主事件循环
    mainloop() 是Tkinter的核心事件循环，进入后程序将持续运行直到窗口关闭
    """
    app = MainWindow()  # 实例化主窗口对象
    app.mainloop()      # 启动Tkinter主事件循环，阻塞等待用户交互


if __name__ == "__main__":
    # 判断是否为直接运行（而非被导入为模块）
    # 当脚本通过 python main.py 直接执行时，调用main()启动应用
    main()
