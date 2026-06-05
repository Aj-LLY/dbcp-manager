"""
项目卡片模块 - 在看板列中以卡片形式展示单个等保测评项目

本模块包含 ProjectCard 类，是系统的核心 UI 组件之一。

相关模块：
  - utils.tooltip: ToolTip 类和 add_tooltip 函数（鼠标悬浮提示）
  - ui.dialog_report_print: show_report_dialog 函数和 XLSX 生成函数（报告打印）

ProjectCard 核心功能：
  - 项目信息展示：公司名称、系统名称、等级、属地、证书编号、截止日期
  - 左侧颜色条：根据截止日期显示绿色（正常）/ 橙色（临近）/ 红色（超期）/ 灰色（无日期）
  - 阶段移动：左箭头（◀）/ 右箭头（▶）按钮，快速将项目移到上/下一阶段
  - 操作按钮：详情、编辑、复制、打开文件夹、重命名、打包、报告打印
  - 选中高亮：单击卡片显示蓝色加粗边框（全局单选）
  - 悬停效果：鼠标进入时背景色变化提示可交互

技术要点：
  - 事件冒泡：通过递归绑定将单击/双击/进入/离开事件绑定到所有子组件（按钮除外）
  - 递归背景色设置：选中/悬停时批量更新子组件背景色（排除固定颜色的功能按钮）
  - 报告打印：弹出编辑确认对话框 -> 创建 XLSX 打印信息表 -> 复制相关文件

依赖关系：
  - models.Project：项目数据实体类
  - utils.Config：全局 UI 配置（字体、颜色、尺寸等）
  - utils.tooltip.add_tooltip：文件操作按钮悬浮提示
  - ui.dialog_report_print：报告打印对话框和 XLSX 生成
"""

# =============================================================================
# 导入区
# =============================================================================

import tkinter as tk  # Python 标准 GUI 库，提供 Frame、Label、Button、Canvas 等组件
from datetime import date  # 日期类，用于截止日期的计算和比较

# ---- 模型层 ----
from models.project import Project  # 项目实体类：包含名称、编号、截止日期、阶段归属等所有字段

# ---- 工具层 ----
from utils.config import Config  # 全局配置类：提供字体、颜色、尺寸预警天数等 UI 常量
from utils.tooltip import add_tooltip  # 文件操作按钮悬浮提示

# ---- 报告打印对话框 ----
from ui.dialog_report_print import (
    show_report_dialog,  # 报告打印前的编辑确认对话框（14 个可编辑字段）
    _create_report_xlsx,  # 创建 XLSX 基础结构
    _create_report_xlsx_data,  # 根据编辑框数据创建 XLSX
)


# =============================================================================
# ProjectCard 类 - 项目卡片主组件
# =============================================================================

class ProjectCard(tk.Frame):
    """项目卡片组件 - 继承自 tk.Frame，作为看板列中的项目展示卡片

    卡片布局（从左到右）：
      ┌──┬────┬──────────────────────────────┬────┬──┐
      │色│ ◀  │         内容区域              │ ▶  │  │
      │条│    │  公司名称 / 系统名称           │    │  │
      │  │    │  等级 · 属地 · 证书编号        │    │  │
      │4 │    │  截止日期                     │    │  │
      │p │    │  ┌──────┬──────┬──────┐      │    │  │
      │x │    │  │ 详情 │ 编辑 │ 复制 │      │    │  │
      │  │    │  └──────┴──────┴──────┘      │    │  │
      │  │    │  ┌───┬───┬───┬───┐         │    │  │
      │  │    │  │📂│📝│📦│📄│         │    │  │
      │  │    │  └───┴───┴───┴───┘         │    │  │
      └──┴────┴──────────────────────────────┴────┴──┘

    交互行为：
      - 单击卡片                -> 选中（蓝色加粗边框）
      - 双击卡片                -> 打开编辑对话框
      - 点击 ◀ 箭头             -> 项目移至上一阶段
      - 点击 ▶ 箭头             -> 项目移至下一阶段
      - 点击"详情"按钮          -> 打开项目详情窗口
      - 点击"编辑"按钮          -> 打开编辑对话框（同双击）
      - 点击"复制"按钮          -> 创建项目副本
      - 点击 📂 按钮            -> 打开项目文件夹
      - 点击 📝 按钮            -> 一键重命名项目文件
      - 点击 📦 按钮            -> 打包过程文档为 ZIP
      - 点击 📄 按钮            -> 报告打印（生成 XLSX）

    Attributes:
        project (Project): 关联的项目实体对象
        is_selected (bool): 当前是否处于选中状态
        on_click: 单击回调函数 -> (card)
        on_double_click: 双击回调函数 -> (card)
        on_detail: 详情按钮回调 -> (card)
        on_edit: 编辑按钮回调 -> (card)
        on_copy: 复制按钮回调 -> (card)
        on_move_prev: 左箭头回调 -> (card)
        on_move_next: 右箭头回调 -> (card)
    """

    def __init__(self, parent, project: Project, **kwargs):
        """初始化项目卡片组件

        Args:
            parent: 父级容器（通常为 KanbanColumn 中的 cards_frame）
            project: 关联的项目实体对象（包含所有业务字段）
            **kwargs: 传递给父类 tk.Frame 的额外关键字参数
        """
        # 调用父类构造方法，设置卡片默认样式
        super().__init__(parent, bg=Config.CARD_BG,  # 白色卡片背景
                         highlightbackground=Config.CARD_BORDER,  # 浅灰边框
                         highlightthickness=1,  # 1px 边框宽度
                         cursor="hand2",  # 手型光标提示可点击
                         **kwargs)

        # ---- 公共属性 ----
        self.project = project  # 主项目引用（向后兼容，等价于 projects[0]）
        self.projects = [project]  # 合并后的项目列表（同公司同阶段的全部项目）
        self.is_selected = False

        # ---- 回调函数指针（由 KanbanBoard 创建卡片后设置） ----
        self.on_click = None  # 单击 -> 选中/取消选中
        self.on_double_click = None  # 双击 -> 打开编辑对话框
        self.on_detail = None  # "详情"按钮 -> 打开详情窗口
        self.on_edit = None  # "编辑"按钮 -> 打开编辑对话框
        self.on_copy = None  # "复制"按钮 -> 创建项目副本
        self.on_move_prev = None  # ◀ 左箭头 -> 移至上一阶段
        self.on_move_next = None  # ▶ 右箭头 -> 移至下一阶段

        # ---- 构建 UI 和绑定事件 ----
        self._build_ui()  # 构建卡片内部的完整 UI 布局
        self._bind_events()  # 为所有子组件递归绑定鼠标事件

    # ==================================================================================
    # UI 构建
    # ==================================================================================

    def _build_ui(self):
        """构建卡片完整布局

        布局顺序（从左到右）：
          1. 左侧颜色条（4px，状态指示）
          2. 左箭头按钮（◀）
          3. 中间内容区域（项目信息 + 操作按钮）
          4. 右箭头按钮（▶）
        """
        # 根据截止日期获取状态指示颜色
        status_color = self._get_status_color()  # 绿色=正常 / 橙色=临近 / 红色=超期 / 灰色=无日期

        # ========== 1. 左侧颜色条（4px 宽垂直色条） ==========
        self._color_bar = tk.Frame(self, bg=status_color, width=4)  # 状态色背景，固定 4px 宽
        self._color_bar.pack(side=tk.LEFT, fill=tk.Y)  # 左侧，垂直填充
        self._color_bar.pack_propagate(False)  # 禁止内容撑开，保持 4px 宽度

        # ========== 2. 左箭头按钮（◀） ==========
        self._prev_btn = tk.Button(
            self, text="\u25c0",  # Unicode ◀ 字符
            command=self._on_prev_click,  # 点击 -> 调用左箭头处理
            bg=Config.CARD_BG, fg="#b0b8c1",  # 卡片背景色，浅灰文字
            font=(Config.FONT_FAMILY, 8),  # 小号字体
            relief="flat", borderwidth=0,  # 扁平样式，无边框
            cursor="hand2", padx=3, pady=0,  # 手型光标，紧凑内边距
            activebackground=Config.CARD_HOVER_BG, activeforeground="#2c3e50",  # 悬停时高亮
        )
        self._prev_btn.pack(side=tk.LEFT, fill=tk.Y)  # 左侧，垂直填充

        # ========== 3. 中间内容区域 ==========
        self._content = tk.Frame(self, bg=Config.CARD_BG)  # 内容容器，白色背景
        self._content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,  # 填充剩余空间
                           padx=6, pady=(8, 4))  # 水平 6px 内边距，上方 8px 下方 4px

        # --- 3a. 公司名称（居中、粗体主标题） ---
        company_display = self.project.company_name or self.project.system_name or "\u65e0\u540d\u79f0"
        if len(company_display) > 14:
            company_display = company_display[:13] + "\u2026"
        self._company_label = tk.Label(
            self._content, text=company_display, bg=Config.CARD_BG,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
            anchor="center", fg="#2c3e50",
        )
        self._company_label.pack(fill=tk.X)

        # --- 3b. 系统行: 系统名称 + 等级 + 证书状态 ---
        # 去重：相同 system_name 只显示一次，取第一个项目的等级和证书
        seen = set()
        for p in self.projects:
            sn = p.system_name or ""
            if not sn or sn in seen:
                continue
            seen.add(sn)
            display = sn if len(sn) <= 14 else sn[:13] + "\u2026"
            extras = ""
            if p.level:
                extras += f"  {p.level}"
            if p.cert_number:
                extras += "  \u2705"  # ✅
            else:
                extras += "  \u26a0\ufe0f"  # ⚠️
            row_text = f"{display}{extras}"
            lbl = tk.Label(self._content, text=row_text, bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                anchor="center", fg="#5d6d7e")
            lbl.pack(fill=tk.X)
        if not seen:
            pass
        # --- 3c. 系统安全等级（居中、小字、紫色） ---
        if self.project.level:
            self._level_label = tk.Label(
                self._content, text=self.project.level,  # 显示等级（如"三级"）
                bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),  # 较小字号
                anchor="center", fg="#8e44ad",  # 紫色文字
            )
            self._level_label.pack(fill=tk.X)
        else:
            self._level_label = None  # 无等级时不显示

        # --- 3d. 所属地（居中、小字、灰色） ---
        if self.project.location:
            self._loc_label = tk.Label(
                self._content, text=self.project.location,  # 显示所在地
                bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                anchor="center", fg="#7f8c8d",  # 灰蓝文字
            )
            self._loc_label.pack(fill=tk.X)
        else:
            self._loc_label = None  # 无属地时不显示

        # --- 3e. 证书编号 / 备案状态（居中） ---
        if self.project.cert_number:  # 有证书编号 -> 已备案状态
            cert_display = self.project.cert_number
            if len(cert_display) > 18:  # 编号过长截断
                cert_display = cert_display[:17] + "\u2026"
            self._cert_label = tk.Label(
                self._content, text="\U0001f4dc \u5df2\u5907\u6848 " + cert_display,  # 📜 已备案 + 编号
                bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                anchor="center", fg="#27ae60",  # 绿色
            )
        else:  # 无证书编号 -> 未备案状态
            self._cert_label = tk.Label(
                self._content, text="\U0001f4dc \u672a\u5907\u6848",  # 📜 未备案
                bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                anchor="center", fg="#e67e22",  # 橙色
            )
        self._cert_label.pack(fill=tk.X)

        # --- 3f. 交付截止日期（居中、带剩余天数提示） ---
        deadline_text = self._format_deadline()  # 格式化的日期文本（含图标和天数）
        fg_color = self._get_deadline_color()  # 根据紧急性获取文字颜色
        self._deadline_label = tk.Label(
            self._content, text=deadline_text, bg=Config.CARD_BG,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            anchor="center", fg=fg_color,  # 动态颜色
        )
        self._deadline_label.pack(fill=tk.X, pady=(2, 0))  # 上方 2px 间距

        # --- 3g. 操作按钮第 1 行：详情 / 编辑 / 复制（居中布局） ---
        btn_frame = tk.Frame(self._content, bg=Config.CARD_BG)  # 按钮行容器
        btn_frame.pack(fill=tk.X, pady=(4, 0))  # 水平填充，上方 4px 间距

        # 使用两个弹性空白 Frame 实现居中效果
        tk.Frame(btn_frame, bg=Config.CARD_BG).pack(side=tk.LEFT, expand=True)  # 左侧弹性空白

        # "详情"按钮
        self._detail_btn = tk.Button(
            btn_frame, text="\u8be6\u60c5",  # \u8be6\u60c5 = 详情
            command=self._on_detail_click,
            bg="#ecf0f1", fg="#2c3e50",  # 浅灰背景，深灰文字
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=8, pady=1,
            activebackground="#d5dbdb",  # 悬停时更深灰
        )
        self._detail_btn.pack(side=tk.LEFT, padx=(0, 4))  # 右间距 4px

        # "编辑"按钮
        self._edit_btn = tk.Button(
            btn_frame, text="\u7f16\u8f91",  # \u7f16\u8f91 = 编辑
            command=self._on_edit_click,
            bg="#3498db", fg="white",  # 蓝色背景，白色文字
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=8, pady=1,
            activebackground="#2980b9",  # 悬停时深蓝
        )
        self._edit_btn.pack(side=tk.LEFT)

        # "复制"按钮
        self._copy_btn = tk.Button(
            btn_frame, text="\u590d\u5236",  # \u590d\u5236 = 复制
            command=self._on_copy_click,
            bg="#27ae60", fg="white",  # 绿色背景，白色文字
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=8, pady=1,
            activebackground="#1e8449",  # 悬停时深绿
        )
        self._copy_btn.pack(side=tk.LEFT, padx=(4, 0))  # 左间距 4px

        tk.Frame(btn_frame, bg=Config.CARD_BG).pack(side=tk.LEFT, expand=True)  # 右侧弹性空白

        # --- 3h. 操作按钮第 2 行：文件操作按钮（居中布局） ---
        file_btn_frame = tk.Frame(self._content, bg=Config.CARD_BG)
        file_btn_frame.pack(fill=tk.X, pady=(2, 0))  # 水平填充，上方 2px 间距

        tk.Frame(file_btn_frame, bg=Config.CARD_BG).pack(side=tk.LEFT, expand=True)  # 左侧弹性空白

        # "打开文件夹"按钮（📂）
        self._folder_btn = tk.Button(
            file_btn_frame, text="\U0001f4c2",  # 📂 文件夹图标
            command=self._on_folder_click,
            bg="#ecf0f1", fg="#2c3e50",  # 浅灰背景
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=7, pady=1,
            activebackground="#d5dbdb",
        )
        self._folder_btn.pack(side=tk.LEFT, padx=(0, 2))
        add_tooltip(self._folder_btn, "打开项目文件夹")

        # "项目初始化"按钮（🔧）
        self._init_btn = tk.Button(
            file_btn_frame, text="\U0001f527",  # 🔧
            command=self._on_init_click,
            bg="#f0f2f5", fg="#2c3e50",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=7, pady=1,
            activebackground="#d5dbdb",
        )
        self._init_btn.pack(side=tk.LEFT, padx=(2, 2))
        add_tooltip(self._init_btn, "项目初始化（创建子目录和模板文件）")

        # "一键重命名"按钮（📝）
        self._rename_btn = tk.Button(
            file_btn_frame, text="\U0001f4dd",  # 📝 备忘录图标
            command=self._on_rename_click,
            bg="#f0f2f5", fg="#2c3e50",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=7, pady=1,
            activebackground="#d5dbdb",
        )
        self._rename_btn.pack(side=tk.LEFT, padx=(2, 2))
        add_tooltip(self._rename_btn, "批量重命名文件")  # 悬浮提示

        # "打包过程文档"按钮（📦）
        self._zip_btn = tk.Button(
            file_btn_frame, text="\U0001f4e6",  # 📦 包裹图标
            command=self._on_zip_click,
            bg="#f39c12", fg="white",  # 橙色背景
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=7, pady=1,
            activebackground="#e67e22",  # 悬停时深橙
        )
        self._zip_btn.pack(side=tk.LEFT, padx=(2, 2))
        add_tooltip(self._zip_btn, "打包过程文档")  # 悬浮提示

        # "报告打印"按钮（📄）
        self._report_btn = tk.Button(
            file_btn_frame, text="\U0001f4c4",  # 📄 文档图标
            command=self._on_report_print_click,
            bg="#8e44ad", fg="white",  # 紫色背景
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=7, pady=1,
            activebackground="#7d3c98",  # 悬停时深紫
        )
        self._report_btn.pack(side=tk.LEFT, padx=(2, 0))
        add_tooltip(self._report_btn, "报告打印")  # 悬浮提示

        tk.Frame(file_btn_frame, bg=Config.CARD_BG).pack(side=tk.LEFT, expand=True)  # 右侧弹性空白

        # ========== 4. 右箭头按钮（▶） ==========
        self._next_btn = tk.Button(
            self, text="\u25b6",  # Unicode ▶ 字符
            command=self._on_next_click,  # 点击 -> 调用右箭头处理
            bg=Config.CARD_BG, fg="#b0b8c1",
            font=(Config.FONT_FAMILY, 8),
            relief="flat", borderwidth=0,
            cursor="hand2", padx=3, pady=0,
            activebackground=Config.CARD_HOVER_BG, activeforeground="#2c3e50",
        )
        self._next_btn.pack(side=tk.RIGHT, fill=tk.Y)  # 右侧，垂直填充

    # ==================================================================================
    # 日期格式化与状态颜色
    # ==================================================================================

    def _format_deadline(self) -> str:
        """格式化截止日期显示文本

        根据剩余天数生成带图标和提示的日期字符串：
          - 无截止日期：显示"无截止日期"
          - 已超期：日期后显示"(已超期)"
          - 临近截止（<= 7 天）：日期后显示"(剩N天)"
          - 正常：仅显示日期

        Returns:
            str: 格式化后的日期文本，格式如 📅 2026-06-15 (剩5天)
        """
        if not self.project.deadline:  # 项目没有设置截止日期
            return "\u65e0\u622a\u6b62\u65e5\u671f"  # \u65e0\u622a\u6b62\u65e5\u671f = 无截止日期
        text = "\U0001f4c5 " + self.project.deadline  # 📅 日历图标 + 日期字符串
        days_left = self._days_until_deadline()  # 计算距离截止日期的天数
        if days_left < 0:  # 已超过截止日期
            text += " (\u5df2\u8d85\u671f)"  # \u5df2\u8d85\u671f = 已超期
        elif days_left <= Config.DEADLINE_WARNING_DAYS:  # 在预警天数范围内（默认 7 天）
            text += f" (\u5269{days_left}\u5929)"  # \u5269 = 剩, \u5929 = 天
        return text  # 返回完整格式化文本

    def _get_status_color(self) -> str:
        """根据项目截止日期获取左侧颜色条的显示颜色

        颜色含义：
          - 灰色 (#95a5a6): 无截止日期，状态不明
          - 红色 (#e74c3c): 已超期，紧急
          - 橙色 (#f39c12): 临近截止日期（<=7 天），需要关注
          - 绿色 (#2ecc71): 时间充裕，正常进行

        Returns:
            str: CSS 颜色代码
        """
        if not self.project.deadline:  # 无截止日期
            return "#95a5a6"  # 灰色
        days_left = self._days_until_deadline()  # 计算剩余天数
        if days_left < 0:  # 已过期
            return "#e74c3c"  # 红色
        elif days_left <= Config.DEADLINE_WARNING_DAYS:  # 临近截止（<= 7 天）
            return "#f39c12"  # 橙色警告
        return "#2ecc71"  # 绿色正常

    def _get_deadline_color(self) -> str:
        """根据截止日期获取日期标签的文字颜色

        Returns:
            str: CSS 颜色代码（绿/橙/红/灰，与状态色条略有不同的色调）
        """
        if not self.project.deadline:
            return "#95a5a6"  # 灰色
        days_left = self._days_until_deadline()
        if days_left < 0:
            return "#e74c3c"  # 红色
        elif days_left <= Config.DEADLINE_WARNING_DAYS:
            return "#e67e22"  # 橙色
        return "#27ae60"  # 绿色

    def _days_until_deadline(self) -> int:
        """计算距离截止日期的剩余天数

        计算公式：deadline - today（正数 = 未来，负数 = 过去，零 = 今天到期）

        Returns:
            int: 剩余天数，负数为已超期，999 表示无法计算（无日期或格式异常）
        """
        if not self.project.deadline:  # 无截止日期
            return 999  # 返回极大值，在排序和判断中视为"远期"
        try:
            dl = date.fromisoformat(self.project.deadline)  # 将 ISO 格式字符串解析为 date 对象
            return (dl - date.today()).days  # 计算日期差（timedelta.days 返回整数天数）
        except (ValueError, TypeError):  # 日期格式不符合 ISO 标准（如 None、"2026/06/15"等）
            return 999  # 格式化异常时返回极大值，避免崩溃

    # ==================================================================================
    # 按钮点击事件处理
    # ==================================================================================

    def _on_prev_click(self):
        """处理左箭头按钮（◀）的点击事件

        触发外部设置的回调函数，由 KanbanBoard 计算上一阶段的 ID，
        最终由 MainWindow 执行项目阶段移动。
        """
        if self.on_move_prev:  # 回调函数已设置（防御性检查）
            self.on_move_prev(self)  # 调用回调并传入自身引用

    def _on_next_click(self):
        """处理右箭头按钮（▶）的点击事件

        触发外部设置的回调函数，由 KanbanBoard 计算下一阶段的 ID，
        最终由 MainWindow 执行项目阶段移动。
        """
        if self.on_move_next:  # 回调函数已设置（防御性检查）
            self.on_move_next(self)  # 调用回调并传入自身引用

    def _on_detail_click(self):
        """处理"详情"按钮的点击事件 - 打开项目详情窗口"""
        if self.on_detail:
            self.on_detail(self)

    def _on_edit_click(self):
        """处理"编辑"按钮的点击事件 - 打开项目编辑对话框"""
        if self.on_edit:
            self.on_edit(self)

    def _on_copy_click(self):
        """处理"复制"按钮的点击事件 - 复制当前项目创建副本"""
        if self.on_copy:
            self.on_copy(self)

    # ==================================================================================
    # 文件操作按钮事件处理
    # ==================================================================================

    def _on_folder_click(self):
        """处理"打开文件夹"按钮点击 - 在系统文件管理器中打开项目目录

        调用各操作系统的默认文件管理器：
          - Windows：os.startfile(path) 直接打开
          - Linux/macOS：subprocess.run(["xdg-open", path])
        """
        import os, subprocess, sys  # 系统操作和子进程模块
        try:
            path = self._find_project_folder()  # 查找项目文件夹路径
            if path and os.path.isdir(path):  # 路径存在且是目录
                if sys.platform == "win32":  # Windows 系统
                    os.startfile(path)  # 使用 Windows 默认方式打开（类似双击文件夹）
                else:  # 非 Windows 系统（Linux/macOS）
                    subprocess.run(["xdg-open", path])  # 调用 xdg-open 打开
        except Exception:  # 打开失败（权限不足、路径不存在等）
            pass  # 静默处理：打开失败不阻塞主流程

    def _find_project_folder(self) -> str:
        """根据项目信息查找本地文件夹路径

        查找策略（按优先级从高到低）：
          1. 项目存储的 folder_path 属性（最直接，优先使用）
          2. 按公司名 + 系统名 + 创建日期的关键词模糊搜索（兜底方案）

        搜索关键词：
          - 公司名称（清理路径非法字符后）
          - 系统名称（清理路径非法字符后）
          - 创建日期（YYMMDD 格式，取项目 created_at 前 10 位的后 6 位）

        Returns:
            str: 找到的文件夹路径，未找到返回空字符串 ""
        """
        import os, re  # 文件系统和正则模块
        from utils.config import Config  # 配置类（获取数据目录）

        # 策略 1：优先使用项目存储的文件夹路径
        if self.project.folder_path and os.path.isdir(self.project.folder_path):
            return self.project.folder_path  # 直接返回存储的路径

        # 策略 2：按关键词搜索
        base = Config.get_data_dir()  # 获取程序数据根目录
        if not os.path.exists(base):  # 根目录不存在
            return ""  # 无数据目录，返回空
        # 清理名称中的路径非法字符，统一替换为下划线
        cname = (self.project.company_name or "未命名").replace("/", "_").replace("\\", "_")
        sname = (self.project.system_name or "").replace("/", "_").replace("\\", "_")
        date_str = ""  # 日期关键词（默认为空，不参与过滤）
        if self.project.created_at:  # 有创建时间
            date_str = self.project.created_at[:10].replace("-", "")[2:]  # YYYY-MM-DD -> YYMMDD

        # 遍历数据目录，查找匹配的文件夹名
        for name in os.listdir(base):
            full = os.path.join(base, name)  # 拼接完整路径
            if not os.path.isdir(full):  # 非目录跳过
                continue
            # 匹配规则：名称中包含公司名，且（无系统名 或 包含系统名），且（无日期 或 包含日期）
            if cname in name and (not sname or sname in name) and (not date_str or date_str in name):
                return full  # 找到匹配，返回路径
        return ""  # 未找到任何匹配

    # ==================================================================================
    # _on_rename_click - 一键重命名功能
    # ==================================================================================

    def _on_rename_click(self):
        """处理"一键重命名"按钮点击 - 批量修正项目过程文件的命名

        此方法是系统的核心自动化功能之一，执行以下流程：

        1. 查找项目文件夹（按 folder_path 或关键词搜索）
        2. 解压 ZIP 文件并重命名内容：
           - "测评方案评审记录表.zip" -> 解压提取文件
           - "测评报告评审表.zip" -> 解压提取文件（保留终审，删除初审）
        3. 删除包含"初审"的文件
        4. 修正文件命名格式为：{编号}-{公司}-{系统}-{标准名称}.{扩展名}
           - 已带编号的文件（如 "07-测评方案.docx"）：匹配关键词后更正编号和名称
           - 无编号的文件：自动添加编号和名称前缀
        5. 修正子目录命名格式：
           - "报告打印" -> "00-{公司}-{系统}-报告打印"
           - "渗透测试报告" -> "13-{公司}-{系统}-渗透测试报告"
        6. 输出操作报告（显示处理了多少文件、跳过多少文件）

        关键字映射表（key_map）：
          {匹配关键词: (编号, 标准化名称)}，按关键词长度倒序匹配避免误匹配
        """
        import os, re, zipfile, shutil  # 操作系统、正则、ZIP 压缩、文件操作模块
        from tkinter import messagebox  # 消息弹窗

        try:
            root = self._find_project_folder()  # 查找项目文件夹路径
            if not root or not os.path.isdir(root):  # 文件夹不存在
                messagebox.showinfo("提示", "未找到项目文件夹")
                return

            # 生成文件名的前导前缀
            cname = (self.project.company_name or "未命名").replace("/", "_").replace("\\", "_")
            sname = (self.project.system_name or "").replace("/", "_").replace("\\", "_")
            new_prefix = f"{cname}-{sname}"  # 格式：公司名-系统名

            # ---- 关键字映射表 ----
            # 格式：{文件名关键词: (编号, 标准化显示名称)}
            # 按关键词长度倒序匹配，防止"测评方案评审表"误匹配为"测评方案"
            key_map = {
                "保密承诺书": ("02", "保密承诺书"),  # 02 号文件
                "测评调研表": ("03", "测评调研表"),  # 03 号文件
                "测评授权书": ("04", "测评授权书"),  # 04 号文件
                "风险告知书": ("05", "风险告知书"),  # 05 号文件
                "项目计划书": ("06", "项目计划书"),  # 06 号文件
                "测评方案": ("07", "测评方案"),  # 07 号文件（注意：需放在"测评方案评审记录表"之后匹配）
                "归档材料评审记录表": ("08", "测评方案评审表"),  # 08 号文件（历史名称）
                "测评方案评审表": ("08", "测评方案评审表"),  # 08 号文件（标准名称）
                "首次会议记录": ("09", "首次会议记录"),  # 09 号文件
                "测评现场记录表": ("10", "测评现场记录表"),  # 10 号文件
                "问题汇总": ("11", "问题汇总及整改建设书"),  # 11 号文件
                "漏洞扫描报告": ("12", "漏洞扫描报告"),  # 12 号文件
                "项目文档移交清单": ("14", "项目文档移交清单"),  # 14 号文件
                "末次会议记录": ("15", "末次会议记录"),  # 15 号文件
                "测评报告-终稿": ("16", "测评报告-终稿"),  # 16 号文件
                "测评报告评审记录表": ("17", "测评报告评审表"),  # 17 号文件（历史名称）
                "测评报告评审表": ("17", "测评报告评审表"),  # 17 号文件（标准名称）
                "服务情况评价表": ("18", "服务情况评价表"),  # 18 号文件
                "报备表": ("19", "报备表"),
                "渗透测试报告": ("13", "渗透测试报告"),  # 渗透测试报告目录
            }

            renamed = 0  # 重命名计数器（累计处理了多少个项目）
            msgs = []  # 操作报告消息列表（每步操作一条记录）

            # ========== 步骤 1: ZIP 文件解压处理 ==========
            for fname in os.listdir(root):  # 遍历项目根目录所有文件
                fpath = os.path.join(root, fname)  # 拼接文件完整路径
                if not os.path.isfile(fpath) or not fname.lower().endswith(".zip"):  # 跳过非 ZIP 文件
                    continue

                # 处理"测评方案评审记录表.zip" -> 解压并重命名内容为 08
                if "测评方案评审记录表" in fname:
                    try:
                        with zipfile.ZipFile(fpath, "r") as zf:  # 以读取模式打开 ZIP
                            zf.extractall(root)  # 解压全部内容到项目根目录
                        os.remove(fpath)  # 删除原 ZIP 文件
                        renamed += 1  # 计数 +1
                        msgs.append(f"解压: {fname} -> 提取文件")  # 记录操作
                    except Exception as e:  # 解压失败（损坏的 ZIP、权限不足等）
                        msgs.append(f"解压失败: {fname} ({e})")

                # 处理"渗透测试报告.zip" -> 解压到独立文件夹后重命名
                if "渗透测试报告" in fname and "评审" not in fname:
                    try:
                        # 解压到临时目录
                        tmp_dir = os.path.join(root, "_渗透测试报告_tmp")
                        if os.path.exists(tmp_dir):
                            shutil.rmtree(tmp_dir)
                        os.makedirs(tmp_dir)
                        with zipfile.ZipFile(fpath, "r") as zf:
                            zf.extractall(tmp_dir)
                        os.remove(fpath)
                        # 去除 ZIP 内的公共顶层目录前缀
                        items = os.listdir(tmp_dir)
                        if len(items) == 1 and os.path.isdir(os.path.join(tmp_dir, items[0])):
                            # ZIP自带一个顶层目录 -> 直接移动该目录
                            src = os.path.join(tmp_dir, items[0])
                            dst = os.path.join(root, f"13-{new_prefix}-渗透测试报告")
                        else:
                            # 文件散落 -> 创建目标目录，移入所有文件
                            dst = os.path.join(root, f"13-{new_prefix}-渗透测试报告")
                            if not os.path.exists(dst):
                                os.makedirs(dst)
                            for item in items:
                                shutil.move(os.path.join(tmp_dir, item), os.path.join(dst, item))
                            shutil.rmtree(tmp_dir)
                            renamed += 1
                            msgs.append(f"解压: {fname} -> 13-{new_prefix}-渗透测试报告/")
                            continue
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.move(src, dst)
                        shutil.rmtree(tmp_dir)
                        renamed += 1
                        msgs.append(f"解压: {fname} -> 13-{new_prefix}-渗透测试报告/")
                    except Exception as e:
                        msgs.append(f"解压失败: {fname} ({e})")

                # 处理"测评报告评审表.zip" -> 解压（后续会删除初审版本）
                elif "测评报告评审表" in fname:
                    try:
                        with zipfile.ZipFile(fpath, "r") as zf:  # 以读取模式打开
                            zf.extractall(root)  # 解压到项目根目录
                        os.remove(fpath)  # 删除原 ZIP
                        renamed += 1
                        msgs.append(f"解压: {fname} -> 提取文件")
                    except Exception as e:
                        msgs.append(f"解压失败: {fname} ({e})")

            # ========== 步骤 2: 删除初审版本文件 ==========
            for fname in os.listdir(root):
                if "初审" in fname:  # 包含"初审"的文件（如测评报告评审表-初审.docx）
                    try:
                        os.remove(os.path.join(root, fname))  # 直接删除
                        msgs.append(f"删除初审: {fname}")
                    except Exception:  # 删除失败（权限等），静默跳过
                        pass

            # ========== 步骤 3: 批量重命名文件 ==========
            for fname in os.listdir(root):  # 遍历根目录所有文件
                fpath = os.path.join(root, fname)
                if not os.path.isfile(fpath) or fname.endswith(".zip"):  # 跳过 ZIP 和目录
                    continue
                name_no_ext, ext = os.path.splitext(fname)  # 分离文件名和扩展名（"07-测评方案", ".docx"）

                # ---- 情况 A: 文件名已有编号前缀（如 "07-测评方案.docx"） ----
                m = re.match(r"^(\d{2})-(.+)", name_no_ext)  # 匹配 "###-内容" 格式
                if m:  # 已有编号前缀
                    num = m.group(1)  # 当前编号（如 "07"）
                    rest = name_no_ext[len(num) + 1:]  # 编号后面的剩余部分（如 "测评方案.docx"）
                    # 按关键词长度从大到小匹配，避免"测评方案评审表"被"测评方案"先匹配
                    for keyword in sorted(key_map, key=len, reverse=True):
                        if keyword in rest:  # 剩余部分中包含关键字
                            num, target_kw = key_map[keyword]  # 获取正确的编号和标准名称
                            new_name = f"{num}-{new_prefix}-{target_kw}{ext}"  # 构建标准文件名
                            if new_name != fname:  # 需要重命名
                                new_path = os.path.join(root, new_name)
                                if not os.path.exists(new_path):  # 目标文件不存在
                                    os.rename(fpath, new_path)  # 执行重命名
                                    renamed += 1
                                else:  # 目标文件已存在（冲突）
                                    msgs.append(f"跳过(已存在): {new_name}")
                            break  # 匹配到一个关键词后退出内层循环

                # ---- 情况 B: 文件名无编号（如 "测评调研表.docx"） ----
                else:
                    for keyword in sorted(key_map, key=len, reverse=True):  # 按关键词长度倒序
                        if keyword in name_no_ext:  # 文件名中包含关键字
                            num, target_kw = key_map[keyword]  # 获取编号和标准名称
                            new_name = f"{num}-{new_prefix}-{target_kw}{ext}"  # 构建标准名
                            new_path = os.path.join(root, new_name)
                            if not os.path.exists(new_path):  # 不冲突
                                os.rename(fpath, new_path)  # 重命名
                                renamed += 1
                            else:
                                msgs.append(f"跳过(已存在): {new_name}")
                            break  # 匹配到一个后退出

            # ========== 步骤 4: 子目录重命名 ==========
            for dname in os.listdir(root):  # 遍历所有目录
                dpath = os.path.join(root, dname)
                if not os.path.isdir(dpath):  # 跳过文件
                    continue
                for keyword, num in {"报告打印": "00", "渗透测试报告": "13"}.items():
                    if keyword in dname and (cname not in dname or sname not in dname):  # 需要更新前缀
                        new_dname = f"{num}-{new_prefix}-{keyword}"  # 标准目录名
                        new_dpath = os.path.join(root, new_dname)
                        if not os.path.exists(new_dpath):  # 不冲突
                            os.rename(dpath, new_dpath)  # 重命名目录
                            renamed += 1
                        break  # 匹配到一个关键词后退出

            # ========== 步骤 5: 显示操作报告 ==========
            if msgs:  # 有详细操作记录
                msg_text = "\n".join(msgs[:15])  # 取前 15 条
                if len(msgs) > 15:  # 超过 15 条则显示统计
                    msg_text += f"\n...共 {len(msgs)} 条"
                messagebox.showinfo("操作报告", msg_text)  # 弹窗展示
            elif renamed:  # 没有详细记录但统计 > 0
                messagebox.showinfo("完成", f"已处理 {renamed} 个项目")
            else:  # 无需任何修改
                messagebox.showinfo("提示", "所有文件名已是最新，无需修改")

        except Exception as e:  # 捕获所有未预见的异常
            messagebox.showerror("错误", f"操作失败: {e}")  # 弹窗显示错误

    # ==================================================================================
    # _on_zip_click - 打包过程文档功能
    # ==================================================================================

    def _on_init_click(self):
        """项目初始化：创建标准子目录和保密承诺书模板"""
        import os
        from tkinter import messagebox
        try:
            root = self._find_project_folder()
            if not root or not os.path.isdir(root):
                messagebox.showinfo("提示", "未找到项目文件夹")
                return
            cname = (self.project.company_name or "未命名").replace("/", "_").replace("\\", "_")
            sname = (self.project.system_name or "").replace("/", "_").replace("\\", "_")
            created = []; existed = []
            # 01-其他归档文件
            dname = "01-其他归档文件"
            dpath = os.path.join(root, dname)
            if not os.path.exists(dpath):
                os.makedirs(dpath, exist_ok=True); created.append(dname)
            else:
                existed.append(dname)
            # 00-报告打印
            dname = f"00-{cname}-{sname}-报告打印"
            dpath = os.path.join(root, dname)
            if not os.path.exists(dpath):
                os.makedirs(dpath, exist_ok=True); created.append(dname)
            else:
                existed.append(dname)
            # 02-保密承诺书
            nda_name = f"02-{cname}-{sname}-保密承诺书.docx"
            nda_path = os.path.join(root, nda_name)
            if os.path.exists(nda_path):
                existed.append(nda_name)
            else:
                try:
                    from utils.config import Config
                    tpl = os.path.join(Config.get_data_dir(), "templates", "02-保密承诺书模板.docx")
                    if os.path.exists(tpl):
                        import shutil, docx
                        shutil.copy2(tpl, nda_path)
                        doc = docx.Document(nda_path)
                        company = self.project.company_name or ""
                        create_date = self.project.created_at[:10] if self.project.created_at else ""
                        # 替换公司名: 逐run保留格式
                        for p in doc.paragraphs:
                            for run in p.runs:
                                if "XX公司" in run.text or "xx公司" in run.text:
                                    run.text = run.text.replace("XX公司", company).replace("xx公司", company)
                                    break
                        # 清除 split 的 "XX"+"公司" run 对
                        for p in doc.paragraphs:
                            for j in range(len(p.runs) - 1):
                                if p.runs[j].text.strip() == "XX" and p.runs[j+1].text.strip() == "公司":
                                    p.runs[j].text = company; p.runs[j+1].text = ""
                        # 替换日期: 保留每个run格式, 仅替换"XX"
                        if create_date:
                            parts = create_date.split("-")
                            if len(parts) == 3:
                                y, m, d = parts[0], f"{int(parts[1]):02d}", f"{int(parts[2]):02d}"
                                for table in doc.tables:
                                    for row in table.rows:
                                        for cell in row.cells:
                                            for p in cell.paragraphs:
                                                rs = p.runs
                                                if len(rs) >= 6 and all(rs[k].text.strip() == v for k, v in [(0,"XX"),(2,"XX"),(4,"XX")]):
                                                    rs[0].text = y; rs[2].text = m; rs[4].text = d
                                                    break
                        doc.save(nda_path)
                        created.append(nda_name)
                except Exception:
                    pass
            # 弹窗报告
            lines = []
            if created:
                lines.append("--- 已创建 ---")
                lines.extend(f"  + {x}" for x in created)
            if existed:
                lines.append("--- 已存在 ---")
                lines.extend(f"  = {x}" for x in existed)
            messagebox.showinfo("初始化完成", "\n".join(lines) if lines else "无需初始化")
        except Exception as e:
            messagebox.showerror("错误", f"初始化失败: {e}")

    def _on_zip_click(self):
        """处理"打包过程文档"按钮点击 - 将项目过程文件压缩为 ZIP

        打包策略：
          1. 查找项目文件夹
          2. 创建 ZIP 文件（命名格式：{公司}-{系统}-过程文档.zip）
          3. 按预定义的关键词列表筛选需要打包的文件：
             - 保密承诺书、测评调研表、测评授权书、风险告知书
             - 项目计划书、测评方案、首次会议记录、测评现场记录表
             - 问题汇总、漏洞扫描报告、项目文档移交清单、末次会议记录
             - 服务情况评价表、报备表
          4. 特殊处理"渗透测试报告"目录：
             - 如果目录非空：递归打包所有文件（保持目录结构）
             - 如果目录为空：添加空目录条目
          5. 成功打包后弹窗提示；无可打包文件时删除空 ZIP

        排除项：
          - 测评报告-终稿（不入过程文档包）
          - 报告打印相关文件
          - 其他归档文件
        """
        import os, zipfile  # 文件系统和 ZIP 压缩模块
        from tkinter import messagebox  # 消息弹窗

        try:
            root = self._find_project_folder()  # 查找项目文件夹路径
            if not root or not os.path.isdir(root):  # 文件夹不存在
                messagebox.showinfo("提示", "未找到项目文件夹")
                return

            # 构建 ZIP 文件名
            cname = self.project.company_name or "未命名"  # 公司名（取不到用"未命名"）
            sname = self.project.system_name or ""  # 系统名
            zip_name = f"{cname}-{sname}-过程文档.zip"  # ZIP 文件名格式
            zip_path = os.path.join(root, zip_name)  # ZIP 文件完整路径

            # ---- 需要打包的文件关键词列表 ----
            # 文件名中包含这些关键词之一的文件将被包含在 ZIP 中
            pack_keywords = [  # 仅打包 #3-#7 和 #9-#15
                "测评调研表", "测评授权书", "风险告知书",
                "项目计划书", "测评方案",
                "首次会议记录", "测评现场记录表",
                "问题汇总", "漏洞扫描报告",
                "项目文档移交清单", "末次会议记录",
            ]

            count = 0  # 已打包文件/目录计数
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:  # 创建 ZIP（DEFLATED 压缩）
                # --- 第一步：打包匹配关键词的单文件 ---
                for fname in os.listdir(root):  # 遍历根目录
                    fpath = os.path.join(root, fname)
                    if not os.path.isfile(fpath) or fname == zip_name:  # 跳过目录和正在创建的 ZIP
                        continue
                    name_no_ext = os.path.splitext(fname)[0]  # 取文件名（不含扩展名）
                    for kw in pack_keywords:  # 遍历关键词
                        if kw in name_no_ext:  # 文件名匹配关键词
                            zf.write(fpath, fname)  # 写入 ZIP（保持原文件名）
                            count += 1  # 计数 +1
                            break  # 匹配到一个关键词即处理下一个文件

                # --- 第二步：打包渗透测试报告目录（含所有内容） ---
                for dname in os.listdir(root):
                    dpath = os.path.join(root, dname)
                    if os.path.isdir(dpath) and "渗透测试报告" in dname:  # 是目标目录
                        has_files = False  # 目录是否有文件（非空标志）
                        for dirpath, _, filenames in os.walk(dpath):  # 递归遍历目录
                            for fn in filenames:  # 遍历每个文件
                                fp = os.path.join(dirpath, fn)  # 文件完整路径
                                arcname = os.path.relpath(fp, root).replace("\\", "/")  # ZIP 内路径（统一斜杠）
                                zf.write(fp, arcname)  # 写入 ZIP，保持目录结构
                                count += 1
                                has_files = True  # 标记为非空
                        # 如果目录为空，添加空目录条目（保留目录结构）
                        if not has_files:
                            info = zipfile.ZipInfo(dname + "/")  # 创建目录条目（末尾 / 标记为目录）
                            zf.writestr(info, "")  # 写入空内容
                            count += 1

            # ---- 结果处理 ----
            if count > 0:  # 至少打包了一个文件
                messagebox.showinfo("打包完成",
                    f"已打包 {count} 个文件\n{zip_name}")  # 显示打包结果
            else:  # 没有匹配的文件
                os.remove(zip_path)  # 删除空 ZIP 文件
                messagebox.showinfo("提示", "未找到可打包的过程文件")

        except Exception as e:  # 捕获所有异常
            messagebox.showerror("错误", f"打包失败: {e}")  # 弹窗显示错误

    # ==================================================================================
    # _on_report_print_click - 报告打印功能
    # ==================================================================================

    def _on_report_print_click(self):
        """处理"报告打印"按钮点击 - 生成测评报告打印信息并复制相关文件

        完整流程：
          1. 查找项目文件夹（如果找不到则提示并退出）
          2. 弹出 show_report_dialog 编辑确认框，预填项目数据
          3. 用户确认 14 个字段后，查找/创建报告打印子目录
          4. 调用 _create_report_xlsx_data 生成测评报告打印信息.xlsx
          5. 复制相关文件到报告打印目录：
             - "测评授权书"相关文件
             - "风险告知书"相关文件
             - "测评报告-终稿.pdf"（如果有）
             - 过程文档 ZIP（如果有）
          6. 弹窗显示生成结果

        报告打印目录命名：00-{公司}-{系统}-报告打印
        XLSX 文件命名：00-{公司}-{系统}-测评报告打印信息.xlsx
        """
        import os, shutil  # 文件系统操作和高级文件复制（保留元数据）
        from tkinter import messagebox  # 消息弹窗
        from datetime import date  # 当前日期

        try:
            proot = self._find_project_folder()  # 查找项目文件夹根目录
            if not proot or not os.path.isdir(proot):  # 根目录不存在
                messagebox.showinfo("提示", "未找到项目文件夹")
                return

            # ---- 步骤 1: 弹出报告打印编辑确认框 ----
            data = show_report_dialog(
                self,  # 父窗口
                cname=self.project.company_name or "",  # 预填公司名称
                sname=self.project.system_name or "",  # 预填系统名称
                location=(self.project.location or "").split("-")[0]  # 预填所属地（取省/市前缀）
                    if self.project.location else "",  # 无属地则空
                deadline=self.project.deadline or date.today().strftime("%Y-%m-%d"),  # 预填日期
            )
            if not data:  # 用户点击了取消
                return

            # 提取用户确认后的关键字段
            cname = data["cname"]  # 客户公司全称
            sname = data["sname"]  # 系统名称
            prefix = f"{cname}-{sname}"  # 文件名前缀

            # ---- 步骤 2: 查找或创建报告打印目录 ----
            report_dir = None  # 报告打印目录路径
            for dname in os.listdir(proot):  # 在项目根目录中查找
                if "报告打印" in dname and os.path.isdir(os.path.join(proot, dname)):
                    report_dir = os.path.join(proot, dname)  # 找到已存在的报告打印目录
                    break
            if not report_dir:  # 不存在则创建
                report_dir = os.path.join(proot, f"00-{prefix}-报告打印")  # 按标准格式命名
                os.makedirs(report_dir, exist_ok=True)  # 递归创建

            # ---- 步骤 3: 创建测评报告打印信息 XLSX ----
            xlsx_name = f"00-{prefix}-测评报告打印信息.xlsx"  # XLSX 文件名
            xlsx_path = os.path.join(report_dir, xlsx_name)  # XLSX 完整路径
            _create_report_xlsx_data(self.project, xlsx_path, data, report_dir, proot)  # 生成 XLSX

            # ---- 步骤 4: 复制相关文件到报告打印目录 ----
            copied = 0  # 已复制文件计数

            # 复制"测评授权书"和"风险告知书"相关文件
            copy_keywords = ["测评授权书", "风险告知书"]
            for fname in os.listdir(proot):  # 遍历项目根目录
                fpath = os.path.join(proot, fname)
                if not os.path.isfile(fpath):  # 跳过目录
                    continue
                for kw in copy_keywords:  # 遍历复制关键词
                    if kw in fname:  # 文件名匹配关键词
                        shutil.copy2(fpath, os.path.join(report_dir, fname))  # 复制（保留元数据）
                        copied += 1  # 计数
                        break  # 匹配一个即处理下一个文件

                # 复制测评报告终稿 PDF
                if "测评报告-终稿" in fname and fname.lower().endswith(".pdf"):  # 必须是 PDF
                    shutil.copy2(fpath, os.path.join(report_dir, fname))  # 复制到打印目录
                    copied += 1

            # 复制过程文档 ZIP（如果已生成）
            zip_name = f"{cname}-{sname}-过程文档.zip"  # ZIP 文件名
            zip_src = os.path.join(proot, zip_name)  # ZIP 源路径
            if os.path.exists(zip_src):  # ZIP 文件存在
                shutil.copy2(zip_src, os.path.join(report_dir, zip_name))  # 复制
                copied += 1

            # ---- 步骤 5: 显示结果 ----
            messagebox.showinfo("报告打印完成",
                f"已生成 {xlsx_name}\n已复制 {copied} 个文件到报告打印目录")

        except Exception as e:  # 捕获所有异常
            messagebox.showerror("错误", f"报告打印失败: {e}")  # 显示错误

    # ==================================================================================
    # 事件绑定 - 鼠标交互事件的递归绑定
    # ==================================================================================

    def _bind_events(self):
        """为卡片内所有子组件递归绑定鼠标事件

        设计原则：
          - 直接子组件不包括按钮（按钮通过 command 独立处理点击）
          - 递归绑定到每个子组件及其后代，实现整张卡片的统一交互体验
          - 按钮组件被排除，避免干扰其自身的 command 事件

        绑定的事件：
          - <Button-1>：单击 -> 选中/取消选中卡片
          - <Double-Button-1>：双击 -> 打开编辑对话框
          - <Enter>：鼠标进入 -> 切换悬停背景色
          - <Leave>：鼠标离开 -> 恢复默认背景色

        排除的按钮集合（btn_widgets）包含：
          左右箭头按钮、详情/编辑/复制按钮、文件夹/重命名/打包/报告按钮
        """
        btn_widgets = {self._prev_btn, self._next_btn,  # 左右箭头按钮
                       self._detail_btn, self._edit_btn, self._copy_btn,  # 操作按钮
                       self._folder_btn, self._init_btn,  # 文件夹+初始化
                       self._rename_btn, self._zip_btn,  # 重命名+打包
                       self._report_btn}  # 报告打印按钮

        # 先给 Frame 自身绑定事件（捕获卡片边缘区域的鼠标事件）
        self.bind("<Button-1>", self._on_click)  # 鼠标左键单击
        self.bind("<Double-Button-1>", self._on_double_click)  # 鼠标左键双击
        self.bind("<Enter>", self._on_enter)  # 鼠标进入组件区域
        self.bind("<Leave>", self._on_leave)  # 鼠标离开组件区域

        def _bind_recursive(widget):
            """递归函数：遍历组件树，为除按钮外的所有组件绑定鼠标事件

            Args:
                widget: 当前要处理的 Tkinter 组件
            """
            if widget not in btn_widgets:  # 跳过按钮组件（它们有自己的 command 绑定）
                widget.bind("<Button-1>", self._on_click)  # 单击
                widget.bind("<Double-Button-1>", self._on_double_click)  # 双击
                widget.bind("<Enter>", self._on_enter)  # 进入
                widget.bind("<Leave>", self._on_leave)  # 离开
                for child in widget.winfo_children():  # 递归遍历该组件的所有子组件
                    _bind_recursive(child)  # 继续递归

        # 从 Frame 的第一层子组件开始递归绑定（不包括 Frame 自身）
        for child in self.winfo_children():  # 遍历 Frame 的直接子组件
            _bind_recursive(child)  # 进入递归绑定

    # ==================================================================================
    # 鼠标事件处理方法
    # ==================================================================================

    def _on_click(self, event):
        """处理鼠标单击事件 - 转发给外部回调（选中/取消选中）"""
        if self.on_click:
            self.on_click(self)

    def _on_double_click(self, event):
        """处理鼠标双击事件 - 转发给外部回调（打开编辑对话框）"""
        if self.on_double_click:
            self.on_double_click(self)

    def _on_enter(self, event):
        """处理鼠标进入卡片区域 - 切换为悬停背景色

        仅在卡片未选中状态下生效，选中状态不受悬浮影响。
        """
        if not self.is_selected:  # 仅在未选中时生效
            self.configure(bg=Config.CARD_HOVER_BG)  # 设置 Frame 自身背景
            self._set_bg_recursive(self, Config.CARD_HOVER_BG)  # 递归设置所有子组件背景

    def _on_leave(self, event):
        """处理鼠标离开卡片区域 - 恢复默认背景色

        仅在卡片未选中状态下生效，选中状态保持蓝色边框。
        """
        if not self.is_selected:  # 仅在未选中时生效
            self.configure(bg=Config.CARD_BG)  # 恢复 Frame 默认白色背景
            self._set_bg_recursive(self, Config.CARD_BG)  # 递归恢复所有子组件背景

    def _set_bg_recursive(self, widget, color):
        """递归设置组件树的背景色

        遍历整个组件树，将符合条件的组件的背景色统一设置为指定颜色。
        排除以下固定颜色组件（避免覆盖功能按钮的设计颜色）：
          - 主题色按钮：蓝色(#3498db, #2980b9)、绿色(#27ae60, #1abc9c)
          - 状态颜色：橙色(#e67e22, #f39c12)、紫色(#8e44ad, #9b59b6)
          - 红色(#e74c3c)、浅灰(#ecf0f1, #d5dbdb)、灰色(#b0b8c1, #95a5a6)
          - 白色(white)：输入框等

        Args:
            widget: 要处理的根组件
            color: 目标背景色
        """
        try:
            bg = widget.cget("bg")  # 获取组件当前背景色（可能抛出 TclError）
            # 检查当前背景色是否在固定颜色排除列表中
            if bg not in ("#3498db", "#2ecc71", "#e67e22",
                          "#9b59b6", "#e74c3c", "#1abc9c",
                          "#f39c12", "#95a5a6",
                          "#ecf0f1", "#d5dbdb", "#2980b9",
                          "#b0b8c1", "white"):
                widget.configure(bg=color)  # 设置新背景色
        except tk.TclError:  # 某些组件可能不支持 bg 属性（如 Canvas 等的特殊子项）
            pass  # 忽略错误，继续处理其他组件

    # ==================================================================================
    # 选中状态管理
    # ==================================================================================

    def set_selected(self, selected: bool):
        """设置卡片的选中状态

        选中状态效果：
          - 选中 (True)：蓝色 (#2196F3) 2px 加粗边框
          - 取消 (False)：恢复默认浅灰 (#d0d5dd) 1px 边框和白色背景

        Args:
            selected: True = 选中，False = 取消选中
        """
        self.is_selected = selected  # 更新内部选中状态标志
        if selected:  # 设置为选中
            # 蓝色材质风格边框，2px 加粗
            self.configure(highlightbackground="#2196F3",
                           highlightthickness=2)
        else:  # 取消选中
            # 恢复默认边框颜色和宽度
            self.configure(highlightbackground=Config.CARD_BORDER,
                           highlightthickness=1)
            self.configure(bg=Config.CARD_BG)  # 恢复默认白色背景

    def refresh(self):
        """刷新卡片显示（销毁所有子组件并重建 UI）

        当项目数据发生修改后调用，通过销毁并重建的方式更新卡片显示内容。
        重建后自动恢复所有回调函数引用，保证交互功能不丢失。

        使用场景：
          - 项目数据被外部修改（编辑对话框、详情窗口）
          - 需要刷新卡片显示以反映最新数据
        """
        # 保存当前所有回调函数引用（重建后需要恢复）
        saved = {
            "on_click": self.on_click,  # 单击回调
            "on_double_click": self.on_double_click,  # 双击回调
            "on_detail": self.on_detail,  # 详情按钮回调
            "on_edit": self.on_edit,  # 编辑按钮回调
            "on_copy": self.on_copy,  # 复制按钮回调
            "on_move_prev": self.on_move_prev,  # 左箭头回调
            "on_move_next": self.on_move_next,  # 右箭头回调
        }
        for widget in self.winfo_children():  # 销毁所有子组件（释放 Tkinter 资源）
            widget.destroy()
        self._build_ui()  # 重新构建 UI（根据最新的 project 数据）
        self._bind_events()  # 重新绑定鼠标事件
        for k, v in saved.items():  # 恢复保存的回调函数
            setattr(self, k, v)  # 使用 setattr 动态设置属性
