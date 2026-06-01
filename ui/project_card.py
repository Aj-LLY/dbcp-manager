"""
项目卡片组件 - 在看板列中以卡片形式展示单个项目

每个卡片显示项目名称、截止日期和状态颜色标识，
支持点击选中、双击编辑、左右箭头移动阶段、详情/编辑按钮
"""

import tkinter as tk  # 导入Tkinter GUI库，用于构建桌面应用界面组件
from datetime import date  # 导入date类，用于截止日期的计算和比较
from models.project import Project  # 导入Project模型类，表示一个等保测评项目实体
from utils.config import Config  # 导入Config配置类，获取颜色、字体等UI配置常量


class ProjectCard(tk.Frame):
    """项目卡片组件 - 继承自tk.Frame，作为看板列中的项目展示卡片

    展示项目摘要信息，支持多种交互：
    - 单击：选中卡片（高亮边框）
    - 双击：直接打开编辑对话框
    - 左/右箭头：快速移动项目到上/下一阶段
    - 详情按钮：打开项目详情窗口
    - 编辑按钮：打开项目编辑对话框

    Attributes:
        project: 关联的项目实体对象（Project实例）
        is_selected: 当前是否被选中（布尔值）
        on_click: 单击回调函数
        on_double_click: 双击回调函数（编辑）
        on_detail: 查看详情回调函数
        on_edit: 编辑回调函数
        on_move_prev: 移至上一阶段回调函数
        on_move_next: 移至下一阶段回调函数
    """

    def __init__(self, parent, project: Project, **kwargs):
        """初始化项目卡片组件

        Args:
            parent: 父级容器（通常为看板列内的卡片容器）
            project: 关联的项目实体对象
            **kwargs: 传递给父类tk.Frame的额外关键字参数
        """
        # 调用父类初始化，设置卡片背景色、边框颜色和鼠标手型光标
        super().__init__(parent, bg=Config.CARD_BG,
                         highlightbackground=Config.CARD_BORDER,
                         highlightthickness=1,
                         cursor="hand2", **kwargs)

        self.project = project  # 保存关联的项目实体对象引用
        self.is_selected = False  # 初始状态为未选中
        self.on_click = None  # 单击回调函数，由外部设置
        self.on_double_click = None  # 双击回调函数，由外部设置
        self.on_detail = None  # 查看详情回调函数，由外部设置
        self.on_edit = None  # 编辑回调函数，由外部设置
        self.on_copy = None  # 复制项目回调函数，由外部设置
        self.on_move_prev = None  # 左箭头移动回调函数，由外部设置
        self.on_move_next = None  # 右箭头移动回调函数，由外部设置

        self._build_ui()  # 构建卡片内部的UI组件布局
        self._bind_events()  # 绑定鼠标交互事件

    def _build_ui(self):
        """构建卡片布局：左侧颜色条 + 左箭头 | 居中内容 | 右箭头

        卡片整体使用水平布局（左右排列），内容区域包含公司名称、
        系统名称、备案号、截止日期等信息，垂直排列居中显示。
        """
        status_color = self._get_status_color()  # 根据截止日期计算状态颜色（绿/橙/红/灰）

        # ---- 左侧颜色条 ----
        # 4像素宽的垂直色条，用于直观展示项目紧急程度
        self._color_bar = tk.Frame(self, bg=status_color, width=4)
        self._color_bar.pack(side=tk.LEFT, fill=tk.Y)  # 左侧垂直填充
        self._color_bar.pack_propagate(False)  # 禁止子组件影响Frame尺寸（保持4px宽度）

        # ---- 左箭头按钮 ----
        # Unicode \u25c0 为 ◀ 字符，点击可将项目移至上一阶段
        self._prev_btn = tk.Button(
            self, text="\u25c0", command=self._on_prev_click,
            bg=Config.CARD_BG, fg="#b0b8c1",
            font=(Config.FONT_FAMILY, 8),
            relief="flat", borderwidth=0,  # 扁平无边框样式
            cursor="hand2", padx=3, pady=0,
            activebackground=Config.CARD_HOVER_BG, activeforeground="#2c3e50",
        )
        self._prev_btn.pack(side=tk.LEFT, fill=tk.Y)  # 左侧垂直填充

        # ---- 中间内容区域 ----
        self._content = tk.Frame(self, bg=Config.CARD_BG)
        # 填充剩余空间，左右各有4像素内边距，上方6px下方2px
        self._content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=(8, 4))

        # 1. 系统名称（居中，粗体）—— 主标题
        sys_display = self.project.system_name or self.project.company_name or "\u65e0\u540d\u79f0"
        if len(sys_display) > 12:
            sys_display = sys_display[:11] + "\u2026"
        self._sys_label = tk.Label(
            self._content, text=sys_display, bg=Config.CARD_BG,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
            anchor="center", fg="#2c3e50",
        )
        self._sys_label.pack(fill=tk.X)

        # 2. 公司名称（居中）—— 仅当两者都有时显示为副标题
        if self.project.system_name and self.project.company_name:
            company_display = self.project.company_name
            if len(company_display) > 14:
                company_display = company_display[:13] + "\u2026"
            self._company_label = tk.Label(
                self._content, text=company_display, bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                anchor="center", fg="#5d6d7e",
            )
            self._company_label.pack(fill=tk.X)
        else:
            self._company_label = None

        # 3. 系统等级（居中，小字）
        if self.project.level:
            self._level_label = tk.Label(
                self._content, text=self.project.level,
                bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                anchor="center", fg="#8e44ad",
            )
            self._level_label.pack(fill=tk.X)
        else:
            self._level_label = None

        # 4. 证书编号（居中，显示备案状态）
        if self.project.cert_number:
            cert_display = self.project.cert_number
            if len(cert_display) > 18:
                cert_display = cert_display[:17] + "\u2026"
            self._cert_label = tk.Label(
                self._content, text="\U0001f4dc \u5df2\u5907\u6848 " + cert_display,
                bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                anchor="center", fg="#27ae60",
            )
            self._cert_label.pack(fill=tk.X)
        else:
            self._cert_label = tk.Label(
                self._content, text="\U0001f4dc \u672a\u5907\u6848",
                bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                anchor="center", fg="#e67e22",
            )
            self._cert_label.pack(fill=tk.X)

        # 5. 交付日期（居中）
        deadline_text = self._format_deadline()
        fg_color = self._get_deadline_color()
        self._deadline_label = tk.Label(
            self._content, text=deadline_text, bg=Config.CARD_BG,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            anchor="center", fg=fg_color,
        )
        self._deadline_label.pack(fill=tk.X, pady=(2, 0))

        # ---- 底部按钮栏（居中） ----
        btn_frame = tk.Frame(self._content, bg=Config.CARD_BG)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        # 用两个弹性空间夹住按钮实现居中布局
        tk.Frame(btn_frame, bg=Config.CARD_BG).pack(side=tk.LEFT, expand=True)  # 左侧弹性空间

        # 详情按钮 - 打开项目详情窗口
        self._detail_btn = tk.Button(
            btn_frame, text="\u8be6\u60c5", command=self._on_detail_click,
            bg="#ecf0f1", fg="#2c3e50",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0,
            cursor="hand2", padx=8, pady=1,
            activebackground="#d5dbdb",  # 鼠标悬停时背景色
        )
        self._detail_btn.pack(side=tk.LEFT, padx=(0, 4))  # 右侧4像素间距

        # 编辑按钮 - 直接打开项目编辑对话框
        self._edit_btn = tk.Button(
            btn_frame, text="\u7f16\u8f91", command=self._on_edit_click,
            bg="#3498db", fg="white",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0,
            cursor="hand2", padx=8, pady=1,
            activebackground="#2980b9",
        )
        self._edit_btn.pack(side=tk.LEFT)

        # 复制按钮 - 克隆当前项目创建副本
        self._copy_btn = tk.Button(
            btn_frame, text="\u590d\u5236", command=self._on_copy_click,
            bg="#27ae60", fg="white",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0,
            cursor="hand2", padx=8, pady=1,
            activebackground="#1e8449",
        )
        self._copy_btn.pack(side=tk.LEFT, padx=(4, 0))

        tk.Frame(btn_frame, bg=Config.CARD_BG).pack(side=tk.LEFT, expand=True)  # 右侧弹性空间

        # ---- 右箭头按钮 ----
        # Unicode \u25b6 为 ▶ 字符，点击可将项目移至下一阶段
        self._next_btn = tk.Button(
            self, text="\u25b6", command=self._on_next_click,
            bg=Config.CARD_BG, fg="#b0b8c1",
            font=(Config.FONT_FAMILY, 8),
            relief="flat", borderwidth=0,
            cursor="hand2", padx=3, pady=0,
            activebackground=Config.CARD_HOVER_BG, activeforeground="#2c3e50",
        )
        self._next_btn.pack(side=tk.RIGHT, fill=tk.Y)  # 右侧垂直填充

    def _format_deadline(self) -> str:
        """格式化截止日期显示文本

        返回包含日历图标、日期和剩余天数提示的格式化字符串。
        无截止日期时返回"无截止日期"，已超期显示"已超期"警告，
        临近截止日期显示"剩N天"提醒。

        Returns:
            str: 格式化后的日期显示文本
        """
        if not self.project.deadline:
            return "\u65e0\u622a\u6b62\u65e5\u671f"  # "无截止日期"
        text = "\U0001f4c5 " + self.project.deadline  # 日历图标 + 日期
        days_left = self._days_until_deadline()  # 计算距截止日期的剩余天数
        if days_left < 0:
            text += " (\u5df2\u8d85\u671f)"  # 已超期
        elif days_left <= Config.DEADLINE_WARNING_DAYS:
            text += f" (\u5269{days_left}\u5929)"  # 剩N天
        return text

    def _on_prev_click(self):
        """左箭头按钮点击处理：调用on_move_prev回调将项目移至上一阶段"""
        if self.on_move_prev:
            self.on_move_prev(self)

    def _on_next_click(self):
        """右箭头按钮点击处理：调用on_move_next回调将项目移至下一阶段"""
        if self.on_move_next:
            self.on_move_next(self)

    def _on_detail_click(self):
        """详情按钮点击处理：调用on_detail回调打开项目详情窗口"""
        if self.on_detail:
            self.on_detail(self)

    def _on_edit_click(self):
        """编辑按钮点击处理：调用on_edit回调打开项目编辑对话框"""
        if self.on_edit:
            self.on_edit(self)

    def _on_copy_click(self):
        """复制按钮点击处理：调用on_copy回调复制当前项目"""
        if self.on_copy:
            self.on_copy(self)

    def _bind_events(self):
        """绑定鼠标事件到卡片内部所有组件（排除按钮组件，因为它们有独立的command）

        使用递归方式将单击、双击、进入、离开事件绑定到卡片内所有子组件，
        但排除左右箭头和详情/编辑按钮，避免干扰按钮自身的点击事件。
        """
        btn_widgets = {self._prev_btn, self._next_btn,
                       self._detail_btn, self._edit_btn, self._copy_btn}  # 需要排除的按钮组件集合

        # 先给Frame自身绑定事件
        self.bind("<Button-1>", self._on_click)  # 鼠标左键单击
        self.bind("<Double-Button-1>", self._on_double_click)  # 鼠标左键双击
        self.bind("<Enter>", self._on_enter)  # 鼠标进入组件区域
        self.bind("<Leave>", self._on_leave)  # 鼠标离开组件区域

        def _bind_recursive(widget):
            """递归函数：遍历组件树，为除按钮外的所有组件绑定鼠标事件"""
            if widget not in btn_widgets:
                widget.bind("<Button-1>", self._on_click)  # 绑定单击
                widget.bind("<Double-Button-1>", self._on_double_click)  # 绑定双击
                widget.bind("<Enter>", self._on_enter)  # 绑定鼠标进入
                widget.bind("<Leave>", self._on_leave)  # 绑定鼠标离开
                for child in widget.winfo_children():  # 遍历所有子组件
                    _bind_recursive(child)  # 递归处理子组件

        for child in self.winfo_children():  # 从Frame的直接子组件开始递归绑定
            _bind_recursive(child)

    def _on_click(self, event):
        """鼠标单击事件处理：调用外部设置的回调函数"""
        if self.on_click:
            self.on_click(self)

    def _on_double_click(self, event):
        """鼠标双击事件处理：调用外部设置的回调函数（通常打开编辑对话框）"""
        if self.on_double_click:
            self.on_double_click(self)

    def _on_enter(self, event):
        """鼠标进入卡片区域：未选中状态下切换为悬停背景色"""
        if not self.is_selected:
            self.configure(bg=Config.CARD_HOVER_BG)  # 设置Frame自身背景色
            self._set_bg_recursive(self, Config.CARD_HOVER_BG)  # 递归设置子组件背景色

    def _on_leave(self, event):
        """鼠标离开卡片区域：未选中状态下恢复默认背景色"""
        if not self.is_selected:
            self.configure(bg=Config.CARD_BG)  # 恢复Frame默认背景色
            self._set_bg_recursive(self, Config.CARD_BG)  # 递归恢复子组件背景色

    def _set_bg_recursive(self, widget, color):
        """递归设置组件树的背景色

        遍历组件树，将符合条件（非特殊颜色组件）的背景色统一设置为指定颜色。
        排除按钮、状态条等固定颜色的组件，避免覆盖其设计颜色。

        Args:
            widget: 要处理的根组件
            color: 目标背景色
        """
        try:
            bg = widget.cget("bg")  # 获取组件当前背景色
            # 排除特殊功能组件的固定颜色（状态色、按钮色等）
            if bg not in ("#3498db", "#2ecc71", "#e67e22",
                          "#9b59b6", "#e74c3c", "#1abc9c",
                          "#f39c12", "#95a5a6",
                          "#ecf0f1", "#d5dbdb", "#2980b9",
                          "#b0b8c1", "white"):
                widget.configure(bg=color)  # 设置新背景色
        except tk.TclError:
            pass  # 某些组件可能不支持bg属性，忽略异常

    def set_selected(self, selected: bool):
        """设置卡片的选中状态

        选中时显示蓝色加粗边框，取消选中时恢复默认边框。

        Args:
            selected: True表示选中，False表示取消选中
        """
        self.is_selected = selected  # 更新选中状态标志
        if selected:
            # 选中状态：蓝色2像素边框
            self.configure(highlightbackground="#2196F3",
                           highlightthickness=2)
        else:
            # 取消选中：恢复默认边框颜色和宽度
            self.configure(highlightbackground=Config.CARD_BORDER,
                           highlightthickness=1)
            self.configure(bg=Config.CARD_BG)  # 恢复默认背景色

    def refresh(self):
        """刷新卡片显示

        当项目数据更新后，销毁并重建所有UI子组件以反映最新数据。
        重建后保留原有的回调函数引用，避免功能丢失。
        """
        # 保存当前的回调函数引用
        saved = {
            "on_click": self.on_click,
            "on_double_click": self.on_double_click,
            "on_detail": self.on_detail,
            "on_edit": self.on_edit,
            "on_copy": self.on_copy,
            "on_move_prev": self.on_move_prev,
            "on_move_next": self.on_move_next,
        }
        for widget in self.winfo_children():  # 销毁所有子组件
            widget.destroy()
        self._build_ui()  # 重建UI
        self._bind_events()  # 重新绑定事件
        for k, v in saved.items():  # 恢复保存的回调函数
            setattr(self, k, v)

    def _get_status_color(self) -> str:
        """根据截止日期获取左侧状态颜色条的显示颜色

        Returns:
            str: 颜色代码
                - 灰色 (#95a5a6): 无截止日期
                - 红色 (#e74c3c): 已超期
                - 橙色 (#f39c12): 临近截止日期（警告期内）
                - 绿色 (#2ecc71): 正常（时间充裕）
        """
        if not self.project.deadline:
            return "#95a5a6"  # 无截止日期，灰色
        days_left = self._days_until_deadline()  # 计算剩余天数
        if days_left < 0:
            return "#e74c3c"  # 已超期，红色
        elif days_left <= Config.DEADLINE_WARNING_DAYS:
            return "#f39c12"  # 临近截止日期，橙色警告
        return "#2ecc71"  # 时间充裕，绿色

    def _get_deadline_color(self) -> str:
        """根据截止日期获取日期标签的文字颜色

        Returns:
            str: 颜色代码
                - 灰色 (#95a5a6): 无截止日期
                - 红色 (#e74c3c): 已超期
                - 橙色 (#e67e22): 临近截止日期
                - 绿色 (#27ae60): 正常
        """
        if not self.project.deadline:
            return "#95a5a6"
        days_left = self._days_until_deadline()
        if days_left < 0:
            return "#e74c3c"
        elif days_left <= Config.DEADLINE_WARNING_DAYS:
            return "#e67e22"
        return "#27ae60"

    def _days_until_deadline(self) -> int:
        """计算距离截止日期的剩余天数（负数表示已超期）

        通过日期差值计算，today - deadline 得到正数时为已过天数。
        无截止日期或日期格式无效时返回999（视为远期）。

        Returns:
            int: 剩余天数，负数表示已超期
        """
        if not self.project.deadline:
            return 999  # 无截止日期，返回大数视为远期
        try:
            dl = date.fromisoformat(self.project.deadline)  # 解析日期字符串
            return (dl - date.today()).days  # 计算日期差（正数为未来，负数为过去）
        except (ValueError, TypeError):
            return 999  # 日期格式异常，返回大数
