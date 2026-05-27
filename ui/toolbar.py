"""
工具栏组件 - 提供快捷操作按钮

位于主窗口顶部，包含新增项目、编辑流程、查看日志、删除项目等功能按钮
使用图标文字组合，方便用户快速识别
"""

import tkinter as tk  # 导入Tkinter GUI库，用于构建桌面应用界面组件
from utils.config import Config  # 导入Config配置类，获取颜色、字体、应用名称等UI配置常量


class Toolbar(tk.Frame):
    """顶部工具栏 - 继承自tk.Frame

    提供系统主要功能的快捷入口按钮，位于主窗口顶部。
    包含按钮：应用标题、新增项目、编辑流程、删除项目、刷新，
    以及右侧的 WebDAV备份、操作日志按钮。

    Attributes:
        on_add_project: 新增项目按钮回调函数
        on_edit_workflow: 编辑流程按钮回调函数
        on_view_logs: 查看日志按钮回调函数
        on_delete_project: 删除项目按钮回调函数
        on_refresh: 刷新看板按钮回调函数
        on_backup: WebDAV备份按钮回调函数
    """

    def __init__(self, parent, **kwargs):
        """初始化工具栏

        Args:
            parent: 父级容器（主窗口对象）
            **kwargs: 传递给父类tk.Frame的额外关键字参数
        """
        # 调用父类初始化，白色背景，固定高度
        super().__init__(parent, bg="#ffffff",
                         height=Config.TOOLBAR_HEIGHT, **kwargs)
        self.pack_propagate(False)  # 禁止子组件撑开Frame，保持固定高度

        # 回调函数 - 由MainWindow在创建工具栏后设置
        self.on_add_project = None  # 新增项目按钮的回调
        self.on_edit_workflow = None  # 编辑流程按钮的回调
        self.on_view_logs = None  # 查看日志按钮的回调
        self.on_delete_project = None  # 删除项目按钮的回调
        self.on_refresh = None  # 刷新看板按钮的回调
        self.on_backup = None  # WebDAV备份按钮的回调

        self._build_ui()  # 构建工具栏按钮UI布局
        self._add_info_area()  # 添加底部提示区域

    def _build_ui(self):
        """构建工具栏按钮区域

        工具栏采用水平布局：
        - 左侧：应用标题 + 各功能按钮
        - 右侧：WebDAV备份按钮 + 操作日志按钮
        """
        # 左侧按钮区域容器
        btn_area = tk.Frame(self, bg="#ffffff")
        btn_area.pack(side=tk.LEFT, fill=tk.Y, padx=5)  # 左侧放置，垂直填充，水平5px内边距

        # 应用标题 - 显示在工具栏最左侧
        tk.Label(btn_area, text=Config.APP_NAME,
                 bg="#ffffff", fg="#2c3e50",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_TITLE, "bold"),
                 ).pack(side=tk.LEFT, padx=(0, 20))  # 右侧20像素与其他按钮保持间距

        # 新增项目按钮 - 蓝色主题
        self._create_btn(btn_area, "新增项目", "#3498db",
                         lambda: self._call_callback(self.on_add_project))
        # 编辑流程按钮 - 深色主题
        self._create_btn(btn_area, "编辑流程", "#2c3e50",
                         lambda: self._call_callback(self.on_edit_workflow))
        # 删除项目按钮 - 红色主题
        self._create_btn(btn_area, "删除项目", "#e74c3c",
                         lambda: self._call_callback(self.on_delete_project))
        # 刷新按钮 - 绿色主题
        self._create_btn(btn_area, "刷新", "#27ae60",
                         lambda: self._call_callback(self.on_refresh))

        # 右侧区域容器
        right_area = tk.Frame(self, bg="#ffffff")
        right_area.pack(side=tk.RIGHT, fill=tk.Y, padx=5)  # 右侧放置，垂直填充

        # WebDAV备份按钮 - 紫色主题
        self._create_btn(right_area, "WebDAV备份", "#8e44ad",
                         lambda: self._call_callback(self.on_backup))
        # 操作日志按钮 - 灰色主题
        self._create_btn(right_area, "操作日志", "#7f8c8d",
                         lambda: self._call_callback(self.on_view_logs))

    def _create_btn(self, parent, text: str, color: str, command):
        """创建工具栏按钮的工厂方法

        统一工具栏按钮的样式：
        - 白色背景，文字颜色为主题色
        - 扁平无边框样式
        - 手型光标
        - 悬停时浅灰色背景

        Args:
            parent: 父容器Frame
            text: 按钮显示文字
            color: 按钮文字主题色
            command: 按钮点击回调函数
        """
        btn = tk.Button(
            parent, text=text, command=command,
            bg="#ffffff", fg=color,  # 白色背景，彩色文字
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
            borderwidth=1, relief="flat",  # 扁平样式，1像素边框
            activebackground="#f0f2f5", activeforeground=color,  # 点击/悬停时浅灰背景
            cursor="hand2", padx=12, pady=4,  # 手型光标，内边距
        )
        btn.pack(side=tk.LEFT, padx=2)  # 左排列，按钮间距2像素

    def _add_info_area(self):
        """底部提示区域 - 显示操作提示信息

        在工具栏左侧底部显示使用提示文字，帮助用户了解基本操作方式。
        """
        tip_label = tk.Label(
            self, text="\U0001f4a1 提示：双击卡片查看详情 | 点击箭头按钮移动阶段",
            bg="#ffffff", fg="#95a5a6",  # 灰色提示文字
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
        )
        tip_label.pack(side=tk.LEFT, padx=10)  # 左侧放置，水平10像素内边距

    def _call_callback(self, callback):
        """安全调用回调函数 - 仅在回调非None时执行

        防止回调未设置时调用引发TypeError异常。

        Args:
            callback: 要调用的回调函数（可能为None）
        """
        if callback:
            callback()
