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

# ---- 文件操作函数（从本类中提取为独立模块） ----
from ui.card_file_ops import (
    find_project_folder,       # 查找项目文件夹路径
    on_folder_click,           # 在文件管理器中打开项目文件夹
    on_init_click,             # 项目初始化（创建子目录和模板文件）
    on_rename_click,           # 批量重命名过程文件
    on_zip_click,              # 打包过程文档为 ZIP
    on_report_print_click,     # 报告打印按钮处理
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

    def __init__(self, parent, project: Project, last_stage_id: str = None, **kwargs):
        """初始化项目卡片组件

        创建卡片 Frame（白色背景 + 灰色边框），保存项目引用，
        依次构建 UI 布局和绑定鼠标交互事件。

        Args:
            parent: 父级容器（KanbanColumn 的 cards_frame）
            project: 关联的项目实体对象，包含名称、截止日期、阶段等所有字段
            last_stage_id: 流程中最后一个阶段的 ID，用于判断是否为已完成阶段
                （已完成阶段的项目在日期显示中标注"(已完成)"）
            **kwargs: 传递给父类 tk.Frame 的额外关键字参数
        """
        super().__init__(parent, bg=Config.CARD_BG,
                         highlightbackground=Config.CARD_BORDER,
                         highlightthickness=1,
                         cursor="hand2",
                         **kwargs)

        self.project = project
        self.projects = [project]
        self.is_selected = False

        self.on_click = None
        self.on_double_click = None
        self.on_detail = None
        self.on_edit = None
        self.on_copy = None
        self.on_move_prev = None
        self.on_move_next = None
        self.last_stage_id = last_stage_id  # 构造时即确定，_build_ui 中可用

        self._build_ui()
        self._bind_events()

    # ==================================================================================
    # UI 构建
    # ==================================================================================

    def _build_ui(self):
        """构建卡片完整布局

        布局顺序（从左到右）：
          1. 左侧颜色条（8px，状态指示 -- 绿/蓝/黄/红/灰）
          2. 左箭头按钮（◀）-- 移动项目到前一阶段
          3. 中间内容区域：
             a. 公司名称（粗体主标题，居中，超 14 字截断）
             b. 系统行：系统名称 + 等级 + 证书状态图标（✅ 已备案 / ⚠️ 未备案）
             c. 证书编号或备案状态标签（📜 已备案/未备案）
             d. 交付截止日期（含剩余天数或超期天数提示）
             e. 操作按钮第 1 行：详情 | 编辑 | 复制
             f. 操作按钮第 2 行：📂 打开文件夹 | 🔧 初始化 | 📝 重命名 | 📦 打包 | 📄 报告打印
          4. 右箭头按钮（▶）-- 移动项目到下一阶段

        提示：左右箭头按钮在最后一阶段/第一阶段的列中仍然显示但不会响应。
        """
        # 根据截止日期获取状态指示颜色
        status_color = self._get_status_color()

        # ========== 1. 左侧颜色条（8px） ==========
        self._color_bar = tk.Frame(self, bg=status_color, width=8)
        self._color_bar.pack(side=tk.LEFT, fill=tk.Y)
        self._color_bar.pack_propagate(False)

        # ========== 2. 左箭头按钮（◀） ==========
        self._prev_btn = tk.Button(
            self, text="\u25c0",
            command=self._on_prev_click,
            bg=Config.CARD_BG, fg="#b0b8c1",
            font=(Config.FONT_FAMILY, 8),
            relief="flat", borderwidth=0,
            cursor="hand2", padx=3, pady=0,
            activebackground=Config.CARD_HOVER_BG, activeforeground="#2c3e50",
        )
        self._prev_btn.pack(side=tk.LEFT, fill=tk.Y)

        # ========== 3. 中间内容区域 ==========
        self._content = tk.Frame(self, bg=Config.CARD_BG)
        self._content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                           padx=6, pady=(8, 4))

        # --- 3a. 卡片标题：多系统→公司名, 单系统→系统名 ---
        is_multi_card = len(self.projects) > 1 if self.projects else False
        if is_multi_card:
            title = self.project.company_name or "\u65e0\u540d\u79f0"
        else:
            title = self.project.system_name or self.project.company_name or "\u65e0\u540d\u79f0"
        if len(title) > 14:
            title = title[:13] + "\u2026"
        self._company_label = tk.Label(
            self._content, text=title, bg=Config.CARD_BG,
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
        """格式化截止日期文本。

        已结项 → "(已完成)"；超期 → "(已超期N天)"；临近 → "(剩N天)"；正常 → 仅日期。
        """
        if not self.project.deadline:
            return "\u65e0\u622a\u6b62\u65e5\u671f"
        text = "\U0001f4c5 " + self.project.deadline
        if self.last_stage_id and self.project.stage_id == self.last_stage_id:
            text += " (\u5df2\u5b8c\u6210)"  # 已完成
            return text
        days_left = self._days_until_deadline()
        if days_left < 0:
            text += f" (\u5df2\u8d85\u671f{abs(days_left)}\u5929)"
        elif days_left <= Config.DEADLINE_WARNING_DAYS:
            text += f" (\u5269{days_left}\u5929)"
        return text

    def _get_status_color(self) -> str:
        """计算左侧颜色条的状态指示颜色

        状态与颜色的对应关系（从 Config.STATUS_COLORS 读取）：
          - 已完成（completed）：项目处于最后一阶段 -> 绿色
          - 正常（normal）：截止日期在预警天数之外 -> 蓝色/绿色
          - 临近（warning）：距离截止日期 <= DEADLINE_WARNING_DAYS 天 -> 黄色/橙色
          - 超期（overdue）：已超过截止日期 -> 红色
          - 未激活（inactive）：未设置截止日期 -> 灰色

        Returns:
            str: 十六进制颜色字符串（如 "#27ae60"）
        """
        if self.last_stage_id and self.project.stage_id == self.last_stage_id:
            return Config.STATUS_COLORS["completed"]
        if not self.project.deadline:
            return Config.STATUS_COLORS["inactive"]
        days_left = self._days_until_deadline()
        if days_left < 0:
            return Config.STATUS_COLORS["overdue"]
        elif days_left <= Config.DEADLINE_WARNING_DAYS:
            return Config.STATUS_COLORS["warning"]
        return Config.STATUS_COLORS["normal"]

    def _get_deadline_color(self) -> str:
        """日期文字颜色：与状态色条一致"""
        return self._get_status_color()

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

        委托给独立模块 ui.card_file_ops.on_folder_click。
        """
        on_folder_click(self.project)

    def _find_project_folder(self) -> str:
        """根据项目信息查找本地文件夹路径

        委托给独立模块 ui.card_file_ops.find_project_folder。

        Returns:
            str: 找到的文件夹路径，未找到返回空字符串 ""
        """
        return find_project_folder(self.project)

    def _on_rename_click(self):
        """处理"一键重命名"按钮点击 - 批量修正项目过程文件的命名

        委托给独立模块 ui.card_file_ops.on_rename_click。
        """
        on_rename_click(self.project, self, all_projects=self.projects)

    def _on_init_click(self):
        """项目初始化：创建标准子目录和保密承诺书模板

        委托给独立模块 ui.card_file_ops.on_init_click。
        """
        on_init_click(self.project, self, all_projects=self.projects)

    def _on_zip_click(self):
        """处理"打包过程文档"按钮点击 - 将项目过程文件压缩为 ZIP

        委托给独立模块 ui.card_file_ops.on_zip_click。
        """
        on_zip_click(self.project, self, all_projects=self.projects)

    # ==================================================================================
    # _on_report_print_click - 报告打印功能
    # ==================================================================================

    def _on_report_print_click(self):
        """处理"报告打印"按钮点击 - 生成测评报告打印信息并复制相关文件

        委托给独立模块 ui.card_file_ops.on_report_print_click。
        """
        on_report_print_click(self.project, self, all_projects=self.projects)

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
                          "#b0b8c1", "white",
                          "#92d050", "#00b0f0", "#ffc000",
                          "#ff0000", "#d9d9d9"):
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
