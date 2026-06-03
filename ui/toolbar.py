"""
工具栏模块 - 主窗口顶部快捷操作按钮栏

本模块实现应用程序的顶部工具栏（Toolbar），提供核心功能的快捷入口。
工具栏采用水平布局，按钮分区管理：
  - 左侧区域：应用标题、新增项目、编辑流程、删除项目、刷新
  - 右侧区域：WebDAV 备份、操作日志

设计理念：
  - 按钮使用文字 + 主题色方案（蓝色=新增、红色=删除、绿色=刷新、紫色=备份、灰色=日志）
  - 统一扁平无边框样式，悬停时浅灰色背景高亮
  - 通过回调函数模式将按钮事件向外传递，实现组件解耦
  - 底部显示操作提示信息，帮助用户了解基本操作方式

依赖：
  - utils.config.Config：提供应用名称、字体等 UI 配置常量
"""

# =============================================================================
# 导入区
# =============================================================================

import tkinter as tk  # Python 标准 GUI 库，用于创建 Frame、Label、Button 等组件
from utils.config import Config  # 全局配置类：提供应用名称、字体、颜色等 UI 配置常量


class Toolbar(tk.Frame):
    """顶部工具栏组件 - 继承自 tk.Frame

    布局结构：
      ┌──────────────────────────────────────────────────────────────┐
      │ 系统标题   [新增项目] [编辑流程] [删除项目] [刷新]  [备份] [日志] │
      │ 💡 提示：双击卡片查看详情...                                    │
      └──────────────────────────────────────────────────────────────┘

    按钮颜色语义：
      - 蓝色 (#3498db) = 新增项目    （创建操作）
      - 深色 (#2c3e50) = 编辑流程    （配置操作）
      - 红色 (#e74c3c) = 删除项目    （危险操作）
      - 绿色 (#27ae60) = 刷新看板    （刷新操作）
      - 紫色 (#8e44ad) = WebDAV 备份 （远程操作）
      - 灰色 (#7f8c8d) = 操作日志    （审计操作）

    Attributes:
        on_add_project: 新增项目按钮回调函数
        on_edit_workflow: 编辑流程按钮回调函数
        on_view_logs: 查看操作日志按钮回调函数
        on_delete_project: 删除选中项目按钮回调函数
        on_refresh: 刷新看板按钮回调函数
        on_backup: WebDAV 备份按钮回调函数
    """

    def __init__(self, parent, **kwargs):
        """初始化工具栏

        Args:
            parent: 父级容器（通常为 MainWindow 主窗口实例）
            **kwargs: 传递给父类 tk.Frame 的额外关键字参数
        """
        # 调用父类构造方法，白色背景，固定高度（从 Config 读取）
        super().__init__(parent, bg="#ffffff",  # 纯白背景
                         height=Config.TOOLBAR_HEIGHT,  # 固定工具栏高度
                         **kwargs)
        self.pack_propagate(False)  # 禁止子组件撑开 Frame，保持固定高度

        # ---- 回调函数指针（由 MainWindow 在创建工具栏后绑定） ----
        self.on_add_project = None  # "新增项目" -> _on_add_project()
        self.on_edit_workflow = None  # "编辑流程" -> _on_edit_workflow()
        self.on_view_logs = None  # "操作日志" -> _on_view_logs()
        self.on_delete_project = None  # "删除项目" -> _on_delete_selected()
        self.on_refresh = None  # "刷新" -> _refresh_kanban()
        self.on_backup = None  # "WebDAV备份" -> _on_backup()

        # ---- 构建 UI ----
        self._build_ui()  # 创建按钮区域（水平排列）
        self._add_info_area()  # 添加底部操作提示文字

    def _build_ui(self):
        """构建工具栏按钮区域

        布局分为两个区域：
          - 左侧（btn_area）：应用标题 + 新增、编辑流程、删除、刷新按钮
          - 右侧（right_area）：WebDAV备份 + 操作日志按钮
        """
        # ========== 左侧按钮区域容器 ==========
        btn_area = tk.Frame(self, bg="#ffffff")  # 左侧区域 Frame
        btn_area.pack(side=tk.LEFT, fill=tk.Y, padx=5)  # 左对齐，垂直填充，5px 水平边距

        # 应用标题（最左侧，与其他按钮有 20px 间隔）
        tk.Label(btn_area, text=Config.APP_NAME,  # 显示应用名称（如"项目进度管理系统"）
                 bg="#ffffff", fg="#2c3e50",  # 白色背景，深灰色文字
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_TITLE, "bold"),  # 大号粗体
                 ).pack(side=tk.LEFT, padx=(0, 20))  # 左侧放置，右侧 20px 与按钮保持距离

        # 功能按钮（从左到右排列）
        self._create_btn(btn_area, "新增项目", "#3498db",  # 蓝色主题 - 创建操作
                         lambda: self._call_callback(self.on_add_project))  # 安全调用回调
        self._create_btn(btn_area, "编辑流程", "#2c3e50",  # 深色主题 - 配置操作
                         lambda: self._call_callback(self.on_edit_workflow))  # 安全调用回调
        self._create_btn(btn_area, "删除项目", "#e74c3c",  # 红色主题 - 危险操作
                         lambda: self._call_callback(self.on_delete_project))  # 安全调用回调
        self._create_btn(btn_area, "刷新", "#27ae60",  # 绿色主题 - 刷新操作
                         lambda: self._call_callback(self.on_refresh))  # 安全调用回调

        # ========== 右侧区域容器 ==========
        right_area = tk.Frame(self, bg="#ffffff")  # 右侧区域 Frame
        right_area.pack(side=tk.RIGHT, fill=tk.Y, padx=5)  # 右对齐，垂直填充

        # 右侧功能按钮
        self._create_btn(right_area, "WebDAV备份", "#8e44ad",  # 紫色主题 - 远程备份
                         lambda: self._call_callback(self.on_backup))  # 安全调用回调
        self._create_btn(right_area, "操作日志", "#7f8c8d",  # 灰色主题 - 审计查询
                         lambda: self._call_callback(self.on_view_logs))  # 安全调用回调

    def _create_btn(self, parent, text: str, color: str, command):
        """工具栏按钮的工厂方法 - 统一创建风格一致的按钮

        按钮样式规范：
          - 白色背景 + 彩色文字（文字颜色即主题色）
          - 扁平无边框样式（relief="flat"），1px 隐式边框
          - 手型光标（cursor="hand2"）提示可点击
          - 悬停时浅灰背景（activebackground="#f0f2f5"）
          - 紧凑内边距（padx=12, pady=4）

        Args:
            parent: 父容器 Frame（btn_area 或 right_area）
            text: 按钮显示文字
            color: 按钮文字主题色（也是悬停时的文字颜色）
            command: 按钮点击时的回调函数
        """
        btn = tk.Button(
            parent, text=text, command=command,  # 按钮文字和回调
            bg="#ffffff", fg=color,  # 白色背景，彩色文字（主题色）
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),  # 正常字体大小
            borderwidth=1, relief="flat",  # 扁平样式，1px 边框
            activebackground="#f0f2f5", activeforeground=color,  # 悬停/点击时浅灰背景
            cursor="hand2", padx=12, pady=4,  # 手型光标，水平 12px + 垂直 4px 内边距
        )
        btn.pack(side=tk.LEFT, padx=2)  # 左排列，按钮间距 2px

    def _add_info_area(self):
        """添加底部提示信息区域

        在工具栏底部显示一行操作提示，帮助新用户快速了解基本交互方式。
        使用灯泡图标（💡） + 灰色小字，视觉上不喧宾夺主。
        """
        tip_label = tk.Label(
            self, text="\U0001f4a1 提示：双击卡片查看详情 | 点击箭头按钮移动阶段",  # 💡 提示
            bg="#ffffff", fg="#95a5a6",  # 白色背景，灰色提示文字
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),  # 小号字体
        )
        tip_label.pack(side=tk.LEFT, padx=10)  # 左对齐，水平 10px 边距

    def _call_callback(self, callback):
        """安全调用回调函数 - 仅在回调已设置时才执行调用

        防止回调函数未设置（为 None）时调用引发 TypeError 异常。
        这是工具栏按钮与控制器之间的安全适配层。

        Args:
            callback: 要调用的回调函数（可能为 None）
        """
        if callback:  # 回调函数已设置（非 None）
            callback()  # 安全调用
