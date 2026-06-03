"""
日历日期选择器组件模块 -- 等保测评进度管理系统

本模块提供一个弹出式日历面板组件，供用户以可视化方式选择日期。
使用方式非常轻量：只需调用 pick_date() 函数，传入父窗口和可选的初始日期，
即可获得用户选择的日期字符串 (YYYY-MM-DD) 或 None（取消）。

日历面板功能：
  - 月份前后翻页（上一月 / 下一月 / 上一年 / 下一年按钮）
  - 点击日期单元格直接选择
  - 今天高亮标识（浅蓝色背景 + 粗体字体）
  - 选中日期标识（蓝色背景 + 白色文字）
  - 返回 YYYY-MM-DD 格式字符串
  - 底部快捷按钮：今天（选中今天日期）、清除（返回空字符串 ""）
  - 点击面板外部区域自动关闭
  - 使用 overrideredirect(True) 实现无系统标题栏的纯自定义外观

使用示例：
    selected = pick_date(parent, "2026-06-03")
    if selected is None:
        print("用户取消了选择")
    elif selected == "":
        print("用户清除了日期")
    else:
        print(f"用户选择了: {selected}")
"""

# =============================================================================
# 标准库导入
# =============================================================================
import tkinter as tk                    # Tkinter GUI 库：构建桌面应用窗口和组件
from datetime import date, timedelta    # 日期处理：date 表示日期，timedelta 用于日期偏移计算

# =============================================================================
# 项目内部模块导入
# =============================================================================
from utils.config import Config         # 全局配置：字体族、字号等 UI 常量


# =============================================================================
# CalendarPicker -- 弹出式日历选择器
# =============================================================================

class CalendarPicker(tk.Toplevel):
    """弹出式日历选择器组件。

    以无边框顶层窗口（overrideredirect=True）形式呈现，
    在父窗口的日期输入框附近弹出，用户可浏览不同月份并点击日期。
    选中日期后自动关闭并返回结果。

    视觉设计：
      - 导航栏：上一年/上一月/年月标题/下一月/下一年
      - 星期标题行：一 二 三 四 五 六 日
      - 日期网格：逐日绘制，不同状态有不同颜色标识
      - 底部快捷按钮：今天 / 清除

    日期单元格状态样式：
      - 当前选中日期：蓝色背景 (#3498db) + 白色文字
      - 今天：浅蓝色背景 (#e8f4fd) + 深色文字 + 粗体
      - 普通日期：白色背景 (#ffffff) + 深色文字 (#2c3e50)
      - 悬停状态：蓝色背景 + 白色文字

    Attributes:
        result: str | None
            选中日期后为 YYYY-MM-DD 格式字符串；
            用户取消（点击外部或关闭）为 None；
            点击"清除"按钮为空字符串 ""。
    """

    # 类常量定义
    WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]  # 星期标题文字（周一至周日）
    CELL_SIZE = 32                                           # 日期单元格像素大小（预留，当前未使用）

    def __init__(self, parent, initial_date: str = ""):
        """初始化日历选择器面板。

        解析初始日期，确定日历面板当前显示的年月。
        如果 initial_date 为空或解析失败，默认使用今天的日期。

        Args:
            parent: 父级窗口引用（用于定位弹窗位置和模态绑定）。
            initial_date: 初始选中日期字符串，格式为 YYYY-MM-DD。为空则使用今天。
        """
        # 调用父类 Tk.Toplevel 构造器
        super().__init__(parent)
        self.overrideredirect(True)                            # 移除系统标题栏和边框（纯自定义外观）
        self.result = None                                     # 初始化结果（None 表示未选择）

        # ---- 解析日期 ----
        self._today = date.today()                             # 获取今天的日期对象
        if initial_date:
            try:
                self._selected = date.fromisoformat(initial_date)  # 尝试解析初始日期
            except (ValueError, TypeError):
                self._selected = self._today                   # 解析失败时回退到今天
        else:
            self._selected = self._today                       # 无初始日期时默认使用今天

        # 日历面板当前查看的年月（初始为选中日期的年月）
        self._view_year = self._selected.year                  # 当前查看的年份
        self._view_month = self._selected.month                # 当前查看的月份

        # ---- 按顺序执行初始化步骤 ----
        self.configure(bg="#ffffff")                           # 白色背景
        self._build_ui()                                       # ① 构建面板结构框架
        self._draw_calendar()                                  # ② 绘制当月日期网格
        self._position(parent)                                 # ③ 定位在父窗口附近
        self.grab_set()                                        # ④ 设为模态（拦截事件到此窗口）
        self.bind("<FocusOut>", lambda e: self.destroy())      # ⑤ 点击外部时关闭

    def _build_ui(self):
        """构建日历面板的完整框架结构。

        组件层次（从上到下）：
            self._main [Frame, 带灰色外边框的主容器]
              ├── nav [Frame] 导航栏
              │     ├── "◀◀" 上一年按钮 (LEFT)
              │     ├── "◀" 上一月按钮 (LEFT)
              │     ├── 年月标题 Label (CENTER)
              │     ├── "▶" 下一月按钮 (RIGHT)
              │     └── "▶▶" 下一年按钮 (RIGHT)
              ├── week_row [Frame] 星期标题行（一～日）
              ├── self._grid_frame [Frame] 日期网格容器（动态绘制区域）
              └── bottom [Frame] 底部按钮栏
                    ├── "今天" 按钮 (LEFT)
                    └── "清除" 按钮 (RIGHT)
        """
        # 主容器：白色背景，灰色外边框（模拟系统窗口边框效果）
        self._main = tk.Frame(self, bg="#ffffff", padx=6, pady=6,
                              highlightbackground="#c0c4cc",   # 灰色边框颜色
                              highlightthickness=1)            # 1 像素边框厚度
        self._main.pack()

        # ---- 导航栏（月份切换） ----
        nav = tk.Frame(self._main, bg="#ffffff")
        nav.pack(fill=tk.X, pady=(0, 4))

        # "◀◀" 上一年按钮：转到同月上一年
        self._prev_year_btn = tk.Button(
            nav, text="\u25c0\u25c0", command=self._prev_year,
            bg="#ffffff", fg="#7f8c8d", relief="flat",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            cursor="hand2", padx=3, pady=0,
            activebackground="#ecf0f1",
        )
        self._prev_year_btn.pack(side=tk.LEFT)

        # "◀" 上一月按钮：转到上一个月
        self._prev_btn = tk.Button(
            nav, text="\u25c0", command=self._prev_month,
            bg="#ffffff", fg="#2c3e50", relief="flat",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            cursor="hand2", padx=6, pady=0,
            activebackground="#ecf0f1",
        )
        self._prev_btn.pack(side=tk.LEFT)

        # 年月标题：居中显示 "2026年 6月" 格式
        self._month_label = tk.Label(
            nav, text="", bg="#ffffff", fg="#2c3e50",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
            width=14,                                          # 固定宽度以容纳最长标题
        )
        self._month_label.pack(side=tk.LEFT, expand=True)

        # "▶" 下一月按钮
        self._next_btn = tk.Button(
            nav, text="\u25b6", command=self._next_month,
            bg="#ffffff", fg="#2c3e50", relief="flat",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            cursor="hand2", padx=6, pady=0,
            activebackground="#ecf0f1",
        )
        self._next_btn.pack(side=tk.RIGHT)

        # "▶▶" 下一年按钮：转到同月下一年
        self._next_year_btn = tk.Button(
            nav, text="\u25b6\u25b6", command=self._next_year,
            bg="#ffffff", fg="#7f8c8d", relief="flat",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            cursor="hand2", padx=3, pady=0,
            activebackground="#ecf0f1",
        )
        self._next_year_btn.pack(side=tk.RIGHT)

        # ---- 星期标题行：一 ～ 日 ----
        week_row = tk.Frame(self._main, bg="#f0f2f5")         # 浅灰色背景
        week_row.pack(fill=tk.X)
        for day in self.WEEKDAYS:
            lbl = tk.Label(week_row, text=day, bg="#f0f2f5", fg="#7f8c8d",
                           font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                           width=4, height=1)                  # 固定宽高使各列对齐
            lbl.pack(side=tk.LEFT)                             # 从左到右水平排列

        # ---- 日期网格容器（每次重绘时清空并重建） ----
        self._grid_frame = tk.Frame(self._main, bg="#ffffff")
        self._grid_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        # ---- 底部快捷按钮栏 ----
        bottom = tk.Frame(self._main, bg="#ffffff")
        bottom.pack(fill=tk.X, pady=(6, 0))

        # "今天" 按钮：选中今天的日期
        tk.Button(bottom, text="今天", command=self._select_today,
                  bg="#ecf0f1", fg="#2c3e50", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  cursor="hand2", padx=10, pady=2,
                  activebackground="#d5dbdb",
                  ).pack(side=tk.LEFT)

        # "清除" 按钮：清空日期选择（返回空字符串 ""）
        tk.Button(bottom, text="清除", command=self._clear,
                  bg="#ecf0f1", fg="#e74c3c", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  cursor="hand2", padx=10, pady=2,
                  activebackground="#d5dbdb",
                  ).pack(side=tk.RIGHT)

    # =========================================================================
    # 日期网格绘制
    # =========================================================================

    def _draw_calendar(self):
        """绘制当前月份的完整日期网格。

        绘制流程：
          1. 清空旧网格中的所有子组件。
          2. 更新导航栏标题为 "YYYY年 M月" 格式。
          3. 计算当月的第一天和最后一天日期对象。
          4. 确定第一天是星期几（0=周一），用于计算前置空白格数量。
          5. 计算总行数：ceil((前置空白格 + 当月天数) / 7)。
          6. 逐行逐列绘制日期单元格或空白占位格。
        """
        # 清空旧网格内容
        for w in self._grid_frame.winfo_children():
            w.destroy()

        # 更新导航栏标题
        self._month_label.configure(
            text=f"{self._view_year}年 {self._view_month}月"
        )

        # ---- 计算当月第一天和最后一天 ----
        first_day = date(self._view_year, self._view_month, 1)  # 本月1号
        if self._view_month == 12:
            # 12月的下月是次年1月，用次年1月1号减1天得到12月最后一天
            last_day = date(self._view_year + 1, 1, 1) - timedelta(days=1)
        else:
            # 其他月份直接用下月1号减1天
            last_day = date(self._view_year, self._view_month + 1, 1) - timedelta(days=1)

        # ---- 计算布局：第一天是周几（0=周一，6=周日） ----
        weekday_of_first = first_day.weekday()                 # 0=周一, ..., 6=周日

        # 总格子数 = 前置空白格 + 当月天数；行数 = ceil(总格子数 / 7)
        total_cells = weekday_of_first + last_day.day
        rows = (total_cells + 6) // 7                          # 向上取整计算总行数

        # ---- 逐格绘制日期 ----
        cell_day = 1                                           # 当月日数计数器（从1开始递增）
        for row in range(rows):
            row_frame = tk.Frame(self._grid_frame, bg="#ffffff")  # 每行一个 Frame
            row_frame.pack(fill=tk.X)
            for col in range(7):
                if row == 0 and col < weekday_of_first:
                    # 第一行的前置空白格（属于上月日期，显示为空白）
                    tk.Label(row_frame, text="", bg="#ffffff",
                             width=4, height=1).pack(side=tk.LEFT)
                elif cell_day > last_day.day:
                    # 超出本月天数的后置空白格（属于下月日期，显示为空白）
                    tk.Label(row_frame, text="", bg="#ffffff",
                             width=4, height=1).pack(side=tk.LEFT)
                else:
                    # 有效日期单元格：创建日期 Button
                    d = date(self._view_year, self._view_month, cell_day)
                    self._draw_day_cell(row_frame, d)          # 绘制可点击的日期按钮
                    cell_day += 1                              # 日数递增

    def _draw_day_cell(self, parent, day: date):
        """绘制单个日期单元格（可点击的 Button）。

        根据日期属性设置不同的视觉样式：
          - 如果是当前选中的日期：蓝色背景 (#3498db) + 白色文字
          - 如果是今天但未选中：浅蓝色背景 (#e8f4fd) + 深色文字 + 粗体字体
          - 普通日期：白色背景 + 深色文字
          - 悬停状态：蓝色背景 + 白色文字（activebackground / activeforeground）

        Args:
            parent: 行容器 Frame。
            day: 该单元格对应的日期对象。
        """
        is_today = (day == self._today)                        # 判断是否为今天
        is_selected = (day == self._selected)                  # 判断是否为当前选中日期

        # 根据状态确定背景色和文字颜色
        if is_selected:
            bg = "#3498db"                                     # 蓝色背景（选中状态）
            fg = "white"                                       # 白色文字（选中状态）
        elif is_today:
            bg = "#e8f4fd"                                     # 浅蓝色背景（今天高亮）
            fg = "#2c3e50"                                     # 深色文字
        else:
            bg = "#ffffff"                                     # 白色背景（普通日期）
            fg = "#2c3e50"                                     # 深色文字

        # 创建日期按钮（使用 Button 而非 Label 以获得点击和悬停反馈）
        cell = tk.Button(
            parent, text=str(day.day),                         # 显示日数（1～31）
            bg=bg, fg=fg,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0,
            width=4, height=1,
            cursor="hand2",
            activebackground="#3498db",                        # 鼠标悬停时蓝色背景
            activeforeground="white",                          # 鼠标悬停时白色文字
            command=lambda d=day: self._on_select(d),          # 使用闭包捕获当前日期 d
        )
        cell.pack(side=tk.LEFT)                                # 水平从左到右排列

        # 今天日期加粗显示
        if is_today:
            cell.configure(font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL, "bold"))

    # =========================================================================
    # 日期选择与导航
    # =========================================================================

    def _on_select(self, day: date):
        """选中某个日期，将结果设为 YYYY-MM-DD 字符串并关闭日历。

        Args:
            day: 被用户点击选中的日期对象。
        """
        self.result = day.strftime("%Y-%m-%d")                 # 格式化为 YYYY-MM-DD 字符串
        self.destroy()                                          # 关闭日历面板

    def _select_today(self):
        """快捷选中今天的日期。

        result 设为今天的 YYYY-MM-DD 格式字符串，然后关闭日历。
        """
        self.result = self._today.strftime("%Y-%m-%d")         # 今天日期格式化
        self.destroy()

    def _clear(self):
        """清除当前日期选择。

        result 设为空字符串 ""（与 None 区分，表示用户明确清除了日期），
        然后关闭日历。
        """
        self.result = ""                                       # 空字符串表示用户清除
        self.destroy()

    # ---- 月份导航 ----

    def _prev_month(self):
        """切换到上一个月。

        如果当前是1月，退回到上一年的12月；否则月份减1。
        切换后重新绘制日期网格。
        """
        if self._view_month == 1:
            self._view_month = 12
            self._view_year -= 1                               # 跨年：退回到去年12月
        else:
            self._view_month -= 1                              # 月份减1
        self._draw_calendar()                                  # 重新绘制日期网格

    def _next_month(self):
        """切换到下一个月。

        如果当前是12月，进入下一年的1月；否则月份加1。
        """
        if self._view_month == 12:
            self._view_month = 1
            self._view_year += 1                               # 跨年：进入明年1月
        else:
            self._view_month += 1                              # 月份加1
        self._draw_calendar()

    def _prev_year(self):
        """切换到上一年（保持月份不变）。"""
        self._view_year -= 1
        self._draw_calendar()

    def _next_year(self):
        """切换到下一年（保持月份不变）。"""
        self._view_year += 1
        self._draw_calendar()

    # =========================================================================
    # 窗口定位
    # =========================================================================

    def _position(self, parent):
        """将日历面板定位在父窗口的合适位置附近。

        尝试将日历显示在父窗口日期输入框的下方区域。
        如果无法获取父窗口坐标（如窗口已销毁），则使用默认屏幕位置。

        Args:
            parent: 父级窗口引用。
        """
        self.update_idletasks()                                # 等待组件尺寸计算完成
        try:
            # 估算在父窗口日期输入框下方偏左的位置
            x = parent.winfo_rootx() + 30                      # 父窗口 X + 30px 偏移
            y = parent.winfo_rooty() + 120                     # 父窗口 Y + 120px 偏移（在输入框下方）
        except (tk.TclError, AttributeError):
            # 无法获取父窗口位置时使用屏幕默认位置
            x = 400
            y = 300
        self.geometry(f"+{x}+{y}")                             # 设置窗口位置


# =============================================================================
# pick_date -- 便捷函数
# =============================================================================

def pick_date(parent, initial_date: str = "") -> str | None:
    """弹出日历选择器并返回用户选中的日期。

    这是外部调用日历选择器的推荐方式，封装了 CalendarPicker 的创建
    和模态等待逻辑。

    Args:
        parent: 父级窗口（Tk 实例或 TopLevel 实例）。
        initial_date: 初始选中日期字符串，格式为 YYYY-MM-DD。
                      为空则使用当天日期作为日历初始高亮。

    Returns:
        str | None:
            用户点击日期 → YYYY-MM-DD 格式日期字符串
            用户点击"清除" → 空字符串 ""
            用户取消选择（关闭 / 点击外部）→ None
    """
    picker = CalendarPicker(parent, initial_date)              # 创建日历选择器实例
    parent.wait_window(picker)                                 # 阻塞等待，直到日历关闭
    return picker.result                                       # 返回选择结果
