"""
日历日期选择器组件 - 弹出式日历面板，供用户可视化选择日期

支持：
- 月份前后翻页（上一月/下一月按钮）
- 点击日期单元格选择
- 今天高亮标识（浅蓝色背景 + 粗体）
- 选中日期标识（蓝色背景 + 白色文字）
- 返回 YYYY-MM-DD 格式字符串
- 底部的"今天"和"清除"快捷按钮
"""

import tkinter as tk  # 导入Tkinter GUI库，用于构建桌面应用界面组件
from datetime import date, timedelta  # 导入date类用于日期处理，timedelta用于日期加减计算
from utils.config import Config  # 导入Config配置类，获取字体等UI配置常量


class CalendarPicker(tk.Toplevel):
    """弹出式日历选择器 - 继承自tk.Toplevel（无边框顶层窗口）

    点击日期条目旁的按钮后弹出，用户可浏览月份并点选日期。
    使用overrideredirect(True)移除系统标题栏，实现纯自定义外观。

    Attributes:
        result: 选中的日期字符串 (YYYY-MM-DD)，取消为None，清除为空字符串""
    """

    # 常量定义
    WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]  # 星期标题（周一至周日）
    CELL_SIZE = 32  # 日期单元格大小（像素）

    def __init__(self, parent, initial_date: str = ""):
        """初始化日历选择器

        Args:
            parent: 父级窗口（用于定位日历弹出位置）
            initial_date: 初始选中日期 (YYYY-MM-DD格式)，为空则使用今天
        """
        super().__init__(parent)
        self.overrideredirect(True)  # 移除系统标题栏和边框（纯自定义窗口外观）
        self.result = None  # 初始化结果（None表示用户未选择/取消）

        # 解析初始日期和今天日期
        self._today = date.today()  # 获取今天的日期对象
        if initial_date:
            try:
                self._selected = date.fromisoformat(initial_date)  # 解析初始日期
            except (ValueError, TypeError):
                self._selected = self._today  # 解析失败时默认使用今天
        else:
            self._selected = self._today  # 无初始日期时使用今天

        # 设置日历面板当前显示的年份和月份
        self._view_year = self._selected.year  # 当前查看的年份
        self._view_month = self._selected.month  # 当前查看的月份

        self.configure(bg="#ffffff")  # 白色背景
        self._build_ui()  # 构建日历面板UI
        self._draw_calendar()  # 绘制当月日期网格
        self._position(parent)  # 定位在父窗口附近
        self.grab_set()  # 拦截所有事件到此窗口（模态行为）

        # 点击外部关闭 - 当日历失去焦点时自动关闭
        self.bind("<FocusOut>", lambda e: self.destroy())

    def _build_ui(self):
        """构建日历面板的框架结构

        包含：
        - 月份导航栏（上月/下月按钮 + 年月标题）
        - 星期标题行（一~日）
        - 日期网格容器（动态绘制）
        - 底部按钮（今天/清除）
        """
        # 主容器 - 带边框的Frame（模拟窗口边框）
        self._main = tk.Frame(self, bg="#ffffff", padx=6, pady=6,
                              highlightbackground="#c0c4cc",  # 灰色边框
                              highlightthickness=1)  # 1像素边框
        self._main.pack()

        # 月份导航栏
        nav = tk.Frame(self._main, bg="#ffffff")
        nav.pack(fill=tk.X, pady=(0, 4))  # 水平填充，下方4px间距

        # 上一月按钮 - 左箭头图标
        self._prev_btn = tk.Button(
            nav, text="\u25c0", command=self._prev_month,  # ◀ 字符
            bg="#ffffff", fg="#2c3e50", relief="flat",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            cursor="hand2", padx=6, pady=0,
            activebackground="#ecf0f1",
        )
        self._prev_btn.pack(side=tk.LEFT)  # 左侧放置

        # 年月标题标签 - 居中显示 "2024年 1月"
        self._month_label = tk.Label(
            nav, text="", bg="#ffffff", fg="#2c3e50",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
            width=12,  # 固定宽度确保标题居中
        )
        self._month_label.pack(side=tk.LEFT, expand=True)  # 左侧放置，可扩展

        # 下一月按钮 - 右箭头图标
        self._next_btn = tk.Button(
            nav, text="\u25b6", command=self._next_month,  # ▶ 字符
            bg="#ffffff", fg="#2c3e50", relief="flat",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            cursor="hand2", padx=6, pady=0,
            activebackground="#ecf0f1",
        )
        self._next_btn.pack(side=tk.RIGHT)  # 右侧放置

        # 星期标题行 - 显示"一"到"日"
        week_row = tk.Frame(self._main, bg="#f0f2f5")  # 浅灰背景
        week_row.pack(fill=tk.X)  # 水平填充
        for day in self.WEEKDAYS:
            lbl = tk.Label(week_row, text=day, bg="#f0f2f5", fg="#7f8c8d",
                           font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                           width=4, height=1)  # 固定宽高使列对齐
            lbl.pack(side=tk.LEFT)  # 从左到右排列

        # 日期网格容器（每次重绘时销毁并重建内容）
        self._grid_frame = tk.Frame(self._main, bg="#ffffff")
        self._grid_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0))  # 双向填充

        # 底部按钮栏：今天 + 清除
        bottom = tk.Frame(self._main, bg="#ffffff")
        bottom.pack(fill=tk.X, pady=(6, 0))

        # 今天按钮 - 选中今天的日期
        tk.Button(bottom, text="今天", command=self._select_today,
                  bg="#ecf0f1", fg="#2c3e50", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  cursor="hand2", padx=10, pady=2,
                  activebackground="#d5dbdb",
                  ).pack(side=tk.LEFT)

        # 清除按钮 - 清空日期选择（返回空字符串）
        tk.Button(bottom, text="清除", command=self._clear,
                  bg="#ecf0f1", fg="#e74c3c", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  cursor="hand2", padx=10, pady=2,
                  activebackground="#d5dbdb",
                  ).pack(side=tk.RIGHT)  # 右侧放置

    def _draw_calendar(self):
        """绘制当前月份的日期网格

        计算当月第一天和最后一天，确定日历网格的布局，
        逐格绘制日期按钮。空白格（上月/下月）留空。
        """
        # 清空旧网格中的所有子组件
        for w in self._grid_frame.winfo_children():
            w.destroy()

        # 更新导航栏标题
        self._month_label.configure(
            text=f"{self._view_year}年 {self._view_month}月"
        )

        # 计算当月第一天和最后一天
        first_day = date(self._view_year, self._view_month, 1)  # 当月1号
        if self._view_month == 12:
            # 12月的下个月是次年1月
            last_day = date(self._view_year + 1, 1, 1) - timedelta(days=1)
        else:
            # 其他月份直接用下个月的1号减1天
            last_day = date(self._view_year, self._view_month + 1, 1) - timedelta(days=1)

        # 第一天是星期几（0=周一, 6=周日）- 用于计算前置空白格数量
        weekday_of_first = first_day.weekday()

        # 总格子数 = 前置空白格 + 当月天数，然后向上取整为7的倍数行
        total_cells = weekday_of_first + last_day.day
        rows = (total_cells + 6) // 7  # 向上取整计算总行数

        # 逐格绘制日期
        cell_day = 1  # 当前绘制的日期（从1递增）
        for row in range(rows):
            row_frame = tk.Frame(self._grid_frame, bg="#ffffff")  # 每行一个Frame
            row_frame.pack(fill=tk.X)  # 水平填充
            for col in range(7):
                if row == 0 and col < weekday_of_first:
                    # 第一行的前置空白格（上月日期，留空不显示）
                    tk.Label(row_frame, text="", bg="#ffffff",
                             width=4, height=1).pack(side=tk.LEFT)
                elif cell_day > last_day.day:
                    # 超出本月天数的空格（下月日期，留空不显示）
                    tk.Label(row_frame, text="", bg="#ffffff",
                             width=4, height=1).pack(side=tk.LEFT)
                else:
                    # 有效日期单元格
                    d = date(self._view_year, self._view_month, cell_day)
                    self._draw_day_cell(row_frame, d)  # 绘制可点击的日期按钮
                    cell_day += 1  # 日期递增

    def _draw_day_cell(self, parent, day: date):
        """绘制单个日期单元格

        根据日期属性设置不同样式：
        - 已选中日期：蓝色背景 + 白色文字
        - 今天：浅蓝色背景 + 深色文字 + 粗体
        - 普通日期：白色背景 + 深色文字

        Args:
            parent: 父容器（行Frame）
            day: 日期对象
        """
        is_today = (day == self._today)  # 判断是否为今天
        is_selected = (day == self._selected)  # 判断是否为当前选中日期

        # 根据状态确定背景色和文字颜色
        if is_selected:
            bg = "#3498db"  # 蓝色背景（选中）
            fg = "white"    # 白色文字（选中）
        elif is_today:
            bg = "#e8f4fd"  # 浅蓝色背景（今天）
            fg = "#2c3e50"  # 深色文字
        else:
            bg = "#ffffff"  # 白色背景（普通）
            fg = "#2c3e50"  # 深色文字

        # 创建日期按钮（使用Button而非Label以支持点击和悬停效果）
        cell = tk.Button(
            parent, text=str(day.day),  # 显示日数（1-31）
            bg=bg, fg=fg,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0,
            width=4, height=1,
            cursor="hand2",
            activebackground="#3498db",  # 悬停时蓝色背景
            activeforeground="white",    # 悬停时白色文字
            command=lambda d=day: self._on_select(d),  # 使用闭包捕获当前日期d
        )
        cell.pack(side=tk.LEFT)  # 水平排列

        # 今天加粗 - 在日期单元格上应用粗体字体
        if is_today:
            cell.configure(font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL, "bold"))

    def _on_select(self, day: date):
        """选中某个日期

        将选中日期格式化为YYYY-MM-DD字符串存入result，然后关闭日历。

        Args:
            day: 被选中的日期对象
        """
        self.result = day.strftime("%Y-%m-%d")  # 格式化为 YYYY-MM-DD
        self.destroy()  # 关闭日历面板

    def _select_today(self):
        """选中今天的日期 - result设为今天的YYYY-MM-DD格式字符串"""
        self.result = self._today.strftime("%Y-%m-%d")
        self.destroy()

    def _clear(self):
        """清除日期选择 - result设为空字符串（而非None），关闭日历"""
        self.result = ""
        self.destroy()

    def _prev_month(self):
        """翻到上一月

        处理跨年情况：1月上一月为去年12月。
        重新绘制日期网格。
        """
        if self._view_month == 1:
            self._view_month = 12  # 1月->12月
            self._view_year -= 1  # 年份减1
        else:
            self._view_month -= 1  # 月份减1
        self._draw_calendar()  # 重新绘制日历

    def _next_month(self):
        """翻到下一月

        处理跨年情况：12月下一月为次年1月。
        重新绘制日期网格。
        """
        if self._view_month == 12:
            self._view_month = 1  # 12月->1月
            self._view_year += 1  # 年份加1
        else:
            self._view_month += 1  # 月份加1
        self._draw_calendar()  # 重新绘制日历

    def _position(self, parent):
        """定位在父窗口日期输入框下方附近

        尝试将日历显示在父窗口的合适位置，
        如果无法获取父窗口坐标则使用默认位置。

        Args:
            parent: 父级窗口
        """
        self.update_idletasks()  # 等待组件尺寸计算完成
        try:
            # 估算在父窗口日期输入框的下方位置
            x = parent.winfo_rootx() + 30  # 偏移30像素
            y = parent.winfo_rooty() + 120  # 偏移120像素（在输入框下方）
        except (tk.TclError, AttributeError):
            # 无法获取父窗口位置时使用默认位置
            x = 400
            y = 300
        self.geometry(f"+{x}+{y}")  # 设置窗口位置


def pick_date(parent, initial_date: str = "") -> str | None:
    """弹出日历选择器并返回选中日期（便捷函数）

    这是外部调用日历选择器的推荐方式。

    Args:
        parent: 父级窗口
        initial_date: 初始日期 (YYYY-MM-DD格式)

    Returns:
        str | None: 选中的日期字符串，取消返回None，清除返回空字符串""
    """
    picker = CalendarPicker(parent, initial_date)  # 创建日历选择器实例
    parent.wait_window(picker)  # 阻塞等待日历关闭（模态）
    return picker.result  # 返回选择结果
