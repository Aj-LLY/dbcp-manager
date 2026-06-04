"""
等保测评进度管理系统 - 程序入口模块

本模块是应用程序的启动脚本，负责初始化运行环境并启动 GUI 主窗口。

功能说明：
  等保测评进度管理系统是一个基于 Python Tkinter 的桌面端看板应用，
  用于管理等保测评项目的全生命周期进度跟踪和流程管理。

  主要特性：
    - 多列看板视图：按流程阶段（项目启动 -> ... -> 项目归档）可视化展示项目
    - 项目卡片管理：每个项目以卡片形式展示，支持拖拽阶段移动
    - 一键文件操作：批量重命名、过程文档打包、报告打印信息生成
    - 操作日志审计：所有增删改操作自动记录，支持按项目查询
    - WebDAV 远程备份：支持数据备份到远程 WebDAV 服务器

启动方式（源码运行）：
    python main.py

打包方式（生成独立 EXE 文件）：
    pyinstaller --onefile --windowed --name "等保测评进度管理系统" main.py

或使用项目自带的构建脚本：
    python build_exe.py           # 仅构建 EXE
    python build_exe.py --release # 构建 EXE 并创建 GitHub Release

架构层次：
    main.py（入口）
      └── MainWindow（控制器 - 主窗口）
            ├── Toolbar（视图 - 工具栏）
            ├── KanbanBoard（视图 - 看板容器）
            │     └── KanbanColumn（视图 - 阶段列）
            │           └── ProjectCard（视图 - 项目卡片）
            ├── DataService（模型 - 数据持久化）
            ├── ProjectService（业务 - 项目管理）
            ├── WorkflowService（业务 - 流程管理）
            └── LogService（业务 - 日志管理）

依赖：
    - ui.main_window.MainWindow：主窗口类
    - utils.config.Config：全局配置（应用名称、版本号、窗口尺寸等）
"""

# =============================================================================
# 导入区
# =============================================================================

import sys  # 系统模块，用于修改 Python 模块搜索路径（sys.path）
import os   # 操作系统模块，用于获取当前脚本所在目录的绝对路径

# 将项目根目录（main.py 所在目录）插入到 Python 模块搜索路径的最前面
# 这样确保无论从哪个目录运行此脚本，都能正确找到项目内的所有模块
# 例如从 C:\ 运行 "python C:\project\main.py"，sys.path 中会包含 C:\project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow  # 导入主窗口类 - 应用程序的顶层 GUI 窗口控制器


# =============================================================================
# 应用程序入口
# =============================================================================

def main():
    """应用程序主入口函数

    执行流程：
      1. 创建 MainWindow 实例（继承自 tk.Tk 的顶级窗口）
         - 构造函数中初始化所有服务层（Data、Project、Workflow、Log）
         - 构建 UI 组件（Toolbar + KanbanBoard）
         - 加载数据并渲染看板
      2. 调用 mainloop() 启动 Tkinter 主事件循环
         - mainloop() 是 Tkinter 的核心事件驱动循环
         - 进入后程序持续运行，等待用户交互事件
         - 直到窗口关闭时退出，返回操作系统的进程控制

    注意：
      mainloop() 是一个阻塞调用，在窗口关闭之前不会返回。
      所有窗口事件（鼠标点击、键盘输入、定时器等）都由 Tkinter 内部事件循环处理。
    """
    app = MainWindow()
    # 安装全局异常捕获，错误信息可在控制台按钮中查看
    from utils.error_log import install
    install(app)
    app.mainloop()


# =============================================================================
# Python 入口标准判断
# =============================================================================

if __name__ == "__main__":
    # 判断当前脚本是否为直接运行（而非被其他模块 import 导入）
    # 当执行 "python main.py" 时 __name__ 的值为 "__main__"，执行 main()
    # 当执行 "import main" 时 __name__ 的值为 "main"，不执行（避免被导入时自动启动）
    main()
