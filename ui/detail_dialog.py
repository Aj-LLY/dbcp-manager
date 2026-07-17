"""
项目详情对话框模块 -- 等保测评进度管理系统

本模块提供项目详细信息查看和操作界面，以模态对话框形式展示。
主要功能包括：
  - 查看项目完整信息（公司名称、系统名称、证书编号、日期、等级、属地、阶段等）
  - 交付日期超期 / 即将到期预警提示
  - 备注信息只读展示
  - 操作日志摘要（最近 5 条）
  - 阶段移动（上一阶段 / 下一阶段）
  - 编辑项目（弹出 ProjectDialog）
  - 删除项目（带二次确认）
  - 移动阶段后不关闭窗口，通过 refresh_data() 刷新内容

外部使用者应通过 show_detail_dialog() 便捷函数调用，
该函数以事件循环方式运行，支持 move 回调（不关闭窗口）和其他操作返回值。

使用示例：
    result = show_detail_dialog(parent, project, stages, logs, on_move=on_move_callback)
    if result:
        action, data = result   # action ∈ {"edit", "delete"}, data 为相关数据
"""

# =============================================================================
# 标准库导入
# =============================================================================
import tkinter as tk            # Tkinter GUI 库：构建桌面应用窗口和组件
from tkinter import messagebox  # messagebox：警告 / 确认 / 信息弹窗

# =============================================================================
# 项目内部模块导入
# =============================================================================
from models.project import Project         # Project 数据模型：表示一个等保测评项目实体
from models.workflow import WorkflowStage   # WorkflowStage 数据模型：表示流程阶段
from ui.project_dialog import show_project_dialog  # 项目编辑对话框便捷函数
from utils.config import Config            # 全局配置：字体族、字号、截止日期预警天数等常量
from utils.helpers import days_until_deadline  # 辅助函数：计算截止日期的剩余天数（负数表示已超期）


# =============================================================================
# DetailDialog -- 项目详情模态对话框
# =============================================================================

class DetailDialog(tk.Toplevel):
    """项目详情对话框。

    以模态顶层窗口形式展示项目的完整信息并提供操作入口。
    窗口布局：
      - 底部固定按钮栏：上一阶段 / 下一阶段 | 编辑 / 删除项目 / 关闭
      - 可滚动内容区（Canvas + Scrollbar）：
          - 标题行（项目名称）
          - 信息卡片区（浅灰背景）：逐行显示各属性字段
          - 备注信息（只读多行文本框）
          - 操作记录摘要（最近 5 条日志）

    交互行为：
      - 编辑：打开 ProjectDialog，确认后返回 ("edit", dict) 给调用方
      - 删除：确认后返回 ("delete", None) 给调用方
      - 移动阶段：通过 on_move 回调处理（不关闭窗口），然后调用 refresh_data() 刷新
      - 关闭：直接 destroy

    Attributes:
        result: tuple | None
            用户操作结果。格式为 (action, data)，其中 action 为 "edit" 或 "delete"，
            data 为编辑后的表单字典或 None（删除操作）。取消 / 关闭为 None。
    """

    def __init__(self, parent, project: Project,
                 stages: list[WorkflowStage],
                 project_logs: list[dict],
                 all_projects: list = None):
        """初始化项目详情对话框。

        Args:
            parent: 父级窗口。
            project: 要展示详情的目标项目实体。
            stages: 流程阶段列表。
            project_logs: 操作日志列表。
            all_projects: 合并卡片中的所有项目（用于展示系统列表）。
        """
        self._all_projects = all_projects
        # 调用父类 Tk.Toplevel 构造器
        super().__init__(parent)
        self.title(f"项目详情 - {project.name}")             # 标题中显示项目名称
        self._project = project                              # 保存目标项目引用
        self._stages = stages                                # 保存阶段列表引用
        self._logs = project_logs                            # 保存日志列表引用

        self.result = None                                   # 初始化操作结果
        self._move_callback = None                           # 外部设置：移动阶段的回调函数
        self._edit_callback = None                           # 外部设置：编辑项目的回调函数
        self._delete_callback = None                         # 外部设置：删除项目的回调函数

        # ---- 按顺序执行初始化步骤 ----
        self._setup_window()     # ① 配置窗口基本属性
        self._build_ui()         # ② 构建详情界面 UI 布局
        self._center_window()    # ③ 窗口居中
        self.grab_set()          # ④ 设为模态窗口

    def _setup_window(self):
        """配置对话框窗口的基本属性。

        初始大小 520×550，最小尺寸 420×400，允许调整大小，白色背景。
        """
        self.geometry("640x580")         # 初始窗口大小（加宽以完整显示表格）
        self.minsize(480, 400)
        self.resizable(True, True)       # 允许水平和垂直调整
        self.configure(bg="#ffffff")     # 白色背景

    def _build_ui(self):
        """构建详情界面的完整 UI 布局。

        布局结构（从上到下）：
          -- 底部按钮栏（先 pack，确保缩小时不被挤出视口）
              · 上一阶段 / 下一阶段（左侧）
              · 编辑 / 删除项目 / 关闭（右侧）
          -- 可滚动内容区域（Canvas + Scrollbar + 内嵌 Frame）
              · 标题行：项目名称
              · 信息卡片区：浅灰背景，逐行显示属性
              · 备注信息：只读 Text 组件
              · 操作日志：最近 5 条操作记录

        信息卡片字段：
          公司名称、系统名称、证书编号、下证日期、系统等级、
          属地、当前阶段、交付日期（含预警）、创建时间、最后更新
        """
        # =====================================================================
        # 底部固定按钮栏（先 pack，放在 BOTTOM 位置占位）
        # =====================================================================
        bottom_frame = tk.Frame(self, bg="#f0f2f5")          # 底部容器，浅灰色背景
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Frame(bottom_frame, bg="#d0d5dd", height=1).pack(fill=tk.X)  # 顶部分隔线

        # 按钮内层容器
        btn_inner = tk.Frame(bottom_frame, bg="#f0f2f5")
        btn_inner.pack(fill=tk.X, padx=16, pady=8)

        # 统一的按钮样式字典
        btn_style = {"cursor": "hand2", "relief": "flat", "padx": 12, "pady": 5,
                     "font": (Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                     "highlightbackground": "#d0d5dd", "highlightthickness": 1}

        # "上一阶段" -- 将项目移到左侧（前一个）阶段
        tk.Button(btn_inner, text="\u25c0 上一阶段", command=self._move_prev,
                  bg="#ffffff", fg="#2c3e50", activebackground="#f0f2f5",
                  **btn_style).pack(side=tk.LEFT, padx=(0, 5))

        # "下一阶段" -- 将项目移到右侧（后一个）阶段
        tk.Button(btn_inner, text="下一阶段 \u25b6", command=self._move_next,
                  bg="#ffffff", fg="#2c3e50", activebackground="#f0f2f5",
                  **btn_style).pack(side=tk.LEFT)

        # "编辑" -- 蓝色背景，打开 ProjectDialog 编辑项目属性
        tk.Button(btn_inner, text="编辑", command=self._edit_project,
                  bg="#3498db", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=16, pady=6,
                  activebackground="#2980b9",
                  ).pack(side=tk.RIGHT, padx=(8, 0))

        # "删除项目" -- 红色背景，二次确认后永久删除
        tk.Button(btn_inner, text="删除项目", command=self._delete_project,
                  bg="#e74c3c", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=16, pady=6,
                  activebackground="#c0392b",
                  ).pack(side=tk.RIGHT, padx=(8, 0))

        # "关闭" -- 白色背景灰色边框，直接关闭对话框
        tk.Button(btn_inner, text="关闭", command=self.destroy,
                  bg="#ffffff", fg="#2c3e50", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                  relief="flat", padx=18, pady=6,
                  highlightbackground="#d0d5dd", highlightthickness=1,
                  activebackground="#f0f2f5",
                  ).pack(side=tk.RIGHT, padx=(8, 0))

        # =====================================================================
        # 可滚动内容区域（Canvas + Scrollbar）
        # =====================================================================
        canvas = tk.Canvas(self, bg="#ffffff", highlightthickness=0)  # 滚动画布
        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)       # 与滚动条双向绑定

        # 主内容 Frame（所有详情信息放在此处）
        main = tk.Frame(canvas, bg="#ffffff", padx=24, pady=18)
        # 当 main 大小变化时更新 Canvas 的滚动区域
        main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # 在 Canvas 内创建窗口对象并 anchor 到左上角
        canvas.create_window((0, 0), window=main, anchor="nw", tags="content")
        # Canvas 宽度变化时同步调整内部窗口宽度（留 4px 边距给滚动条）
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("content", width=e.width - 4))
        # 鼠标滚轮绑定到 Canvas
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta/120), "units"))

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 保存 Canvas 引用，并将滚轮事件同时绑定到对话框自身以确保始终响应
        self._canvas = canvas
        self.bind("<MouseWheel>", lambda e: self._canvas.yview_scroll(int(-e.delta/120), "units"))

        # =====================================================================
        # 标题行 -- 显示项目名称
        # =====================================================================
        header = tk.Frame(main, bg="#ffffff")
        header.pack(fill=tk.X, pady=(0, 15))

        tk.Label(header, text=self._project.name,
                 bg="#ffffff", fg="#2c3e50",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_HEADER, "bold"),
                 wraplength=400, justify="left",            # 超长自动换行，左对齐
                 ).pack(anchor="w")

        # =====================================================================
        # 信息卡片区 -- 浅灰背景，逐行显示各字段
        # =====================================================================
        info_frame = tk.Frame(main, bg="#f8f9fa", padx=12, pady=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # 公司名称
        self._add_info_row(info_frame, "公司名称",
                           self._project.company_name or "-")
        # 系统列表表格（若有关联项目则展示多行）
        all_projects = (getattr(self, '_all_projects', None)
                       or getattr(self, '_saved_all_projects', None)
                       or [self._project])
        if len(all_projects) > 1:
            # 在独立子 Frame 中用 grid 布局（避免与 info_frame 的 pack 冲突）
            tbl_frame = tk.Frame(info_frame, bg="#f8f9fa")
            tbl_frame.pack(fill=tk.X, pady=(4, 2))
            columns = [("系统名称", 24), ("证书编号", 18), ("下证日期", 12), ("等级", 8)]
            for ci, (txt, w) in enumerate(columns):
                tk.Label(tbl_frame, text=txt, bg="#e9ecef", fg="#2c3e50",
                         font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL, "bold"),
                         width=w, anchor="w", padx=2).grid(row=0, column=ci, sticky="w")
            for ri, p in enumerate(all_projects, 1):
                vals = [p.system_name or "-", p.cert_number or "-",
                        p.issue_date or "-", p.level or "-"]
                for ci, (val, (_, w)) in enumerate(zip(vals, columns)):
                    e = tk.Entry(tbl_frame, bg="#f8f9fa", fg="#2c3e50", relief="flat",
                                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                                 readonlybackground="#f8f9fa", width=w)
                    e.insert(0, val)
                    e.configure(state="readonly")
                    e.grid(row=ri, column=ci, sticky="w", padx=2)
        else:
            self._add_info_row(info_frame, "系统名称", self._project.system_name or "-")
            self._add_info_row(info_frame, "证书编号", self._project.cert_number or "未备案")
            self._add_info_row(info_frame, "下证日期", self._project.issue_date or "-")
            self._add_info_row(info_frame, "系统等级", self._project.level or "-")
        self._add_info_row(info_frame, "属地",
                           self._project.location or "-")
        # 当前阶段名称（通过 stage_id 查找）
        stage_name = self._get_stage_name(self._project.stage_id)
        self._add_info_row(info_frame, "当前阶段", stage_name)

        # ---- 交付日期 -- 附带超期 / 即将到期预警 ----
        deadline = self._project.deadline or "未设置"
        is_last = self._stages and self._project.stage_id == self._stages[-1].id
        if is_last:
            deadline += "  \u2705 \u5df2\u5b8c\u6210"  # ✅ 已完成
        else:
            days_left = days_until_deadline(self._project.deadline) if self._project.deadline else None
            if days_left is not None:
                if days_left < 0:
                    deadline += f"  \u26a0\ufe0f \u5df2\u8d85\u671f {abs(days_left)} \u5929"
                elif days_left <= Config.DEADLINE_WARNING_DAYS:
                    deadline += f"  \u26a1 \u5269\u4f59 {days_left} \u5929"
                else:
                    deadline += f"  \u5269\u4f59 {days_left} \u5929"
        self._add_info_row(info_frame, "交付日期", deadline)

        # 创建时间和最后更新时间的格式化展示
        self._add_info_row(info_frame, "创建时间", self._project.created_at)
        self._add_info_row(info_frame, "最后更新", self._project.updated_at)

        # =====================================================================
        # 备注信息 -- 只读多行文本框
        # =====================================================================
        notes = self._project.notes or "无"
        tk.Label(main, text="备注信息", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                 fg="#2c3e50").pack(anchor="w", pady=(5, 2))

        notes_text = tk.Text(main, height=4, wrap="word",     # 4行可见，按单词换行
                             font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                             bg="#f8f9fa", relief="flat", borderwidth=1)
        notes_text.insert("1.0", notes)                       # 插入备注内容
        notes_text.configure(state="disabled")                # 设为只读（禁止编辑）
        notes_text.pack(fill=tk.X)

        # =====================================================================
        # 操作日志摘要 -- 显示最近 5 条操作记录
        # =====================================================================
        tk.Label(main, text="操作记录（最近5条）", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                 fg="#2c3e50").pack(anchor="w", pady=(10, 2))

        log_frame = tk.Frame(main, bg="#f8f9fa")             # 日志列表容器
        log_frame.pack(fill=tk.X, pady=(0, 5))

        recent_logs = self._logs[:5]                          # 取最近 5 条日志
        if recent_logs:
            for log in recent_logs:
                # 格式化日志行：时间 | 操作类型 | 操作描述
                log_text = f"{log.get('timestamp', '')} | {log.get('action', '')} | {log.get('detail', '')}"
                if len(log_text) > 65:
                    log_text = log_text[:64] + "\u2026"       # 超过65字符截断并添加省略号
                tk.Label(log_frame, text=log_text, bg="#f8f9fa",
                         font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                         fg="#7f8c8d", anchor="w", justify="left",
                         ).pack(fill=tk.X, pady=1, padx=8)
        else:
            # 无日志时的占位提示
            tk.Label(log_frame, text="暂无操作记录", bg="#f8f9fa",
                     font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                     fg="#95a5a6").pack(pady=8)

    def _add_info_row(self, parent, label: str, value: str):
        """在信息卡片区添加一行 "标签全角冒号 值" 格式的信息行。

        每行由两部分组成：
          - 左侧标签列：右对齐、固定宽度、灰色文字的 Label（如 "公司名称："）
          - 右侧值列：只读 Entry，支持文本选择和复制

        Args:
            parent: 父容器 Frame（信息卡片区）。
            label: 字段标签名（如 "公司名称"）。
            value: 字段值字符串（可为空或任何文本）。
        """
        row = tk.Frame(parent, bg="#f8f9fa")                  # 行容器
        row.pack(fill=tk.X, pady=2)                            # 水平填充，行间距 2px

        # 标签列：全角冒号后缀，右对齐，固定宽度 10 字符
        tk.Label(row, text=label + "\uff1a", bg="#f8f9fa",   # \uff1a 是全角冒号
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 fg="#7f8c8d", width=10, anchor="e",
                 ).pack(side=tk.LEFT)

        # 值列：只读 Entry（支持用户选择复制文本）
        val_entry = tk.Entry(row, bg="#f8f9fa", fg="#2c3e50", relief="flat",
                             font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                             readonlybackground="#f8f9fa")
        val_entry.insert(0, value)                             # 插入值
        val_entry.configure(state="readonly")                  # 设为只读
        val_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)

    # =========================================================================
    # 项目操作
    # =========================================================================

    def _edit_project(self):
        """编辑项目按钮处理。

        打开 project_dialog 的 show_project_dialog 对话框进行编辑，
        如果用户确认保存，则将结果设为 ("edit", 表单数据) 并关闭详情窗口。
        """
        all_proj = (getattr(self, '_all_projects', None)
                   or getattr(self, '_saved_all_projects', None))
        result = show_project_dialog(
            self, "编辑项目", self._project, self._stages, all_projects=all_proj,
        )
        if result:                                             # 用户点击了保存
            self.result = ("edit", result)                     # 设置编辑操作结果
            self.destroy()                                     # 关闭详情窗口

    def _delete_project(self):
        """删除项目按钮处理。

        弹出二次确认对话框（askyesno），用户确认后将 self.result
        设置为 ("delete", None) 并关闭窗口。删除操作的实际执行由外部
        MainWindow 负责。
        """
        if messagebox.askyesno("确认删除",
                               f"确定要永久删除项目\u300c{self._project.name}\u300d吗？\n\n"
                               "此操作不可撤销！",
                               parent=self):
            self.result = ("delete", None)                     # 设置删除操作结果
            self.destroy()

    # =========================================================================
    # 阶段移动
    # =========================================================================

    def _move_prev(self):
        """将项目移到上一个流程阶段。

        查找当前阶段在阶段列表中的索引位置，
        如果不在第一个位置（idx > 0），则将 result 设置为移动到前一个阶段 ID。
        如果已是第一个阶段，弹出提示信息。
        """
        idx = self._get_stage_index(self._project.stage_id)    # 获取当前阶段索引
        if idx > 0:                                            # 不是第一个阶段
            self.result = ("move", self._stages[idx - 1].id)   # 移动到前一个阶段
        else:
            messagebox.showinfo("提示", "已经是第一个阶段", parent=self)

    def _move_next(self):
        """将项目移到下一个流程阶段。

        查找当前阶段在阶段列表中的索引位置，
        如果不在最后一个位置，则将 result 设置为移动到后一个阶段 ID。
        """
        idx = self._get_stage_index(self._project.stage_id)
        if idx < len(self._stages) - 1:                        # 不是最后一个阶段
            self.result = ("move", self._stages[idx + 1].id)   # 移动到后一个阶段
        else:
            messagebox.showinfo("提示", "已经是最后一个阶段", parent=self)

    def refresh_data(self, project, stages, logs):
        """刷新详情窗口数据（移动阶段后调用，不关闭窗口重建 UI）。

        移动阶段后 MainWindow 会调用此方法更新项目、阶段和日志数据，
        然后销毁并重建所有子组件以达到刷新效果。

        Args:
            project: 更新后的项目对象。
            stages: 更新后的阶段列表。
            logs: 更新后的日志列表。
        """
        self._project = project                                # 更新项目引用
        self._stages = stages                                  # 更新阶段列表
        self._logs = logs                                      # 更新日志列表
        # 保留多系统数据引用（移动阶段后不丢失）
        if not hasattr(self, '_saved_all_projects'):
            self._saved_all_projects = getattr(self, '_all_projects', None)
        self.title(f"项目详情 - {project.name}")               # 刷新标题
        # 销毁所有子组件
        for w in self.winfo_children():
            w.destroy()
        self._build_ui()                                       # 重建整个 UI
        self.result = None                                     # 清空操作结果
        self.after(200, lambda: setattr(self, '_opening_child', False))  # 延迟清除子窗口标志

    # =========================================================================
    # 辅助查询方法
    # =========================================================================

    def _get_stage_name(self, stage_id: str) -> str:
        """根据阶段 ID 获取对应的阶段名称。

        Args:
            stage_id: 阶段的唯一标识符。

        Returns:
            str: 阶段名称；若未找到匹配的阶段，返回 "未知阶段"。
        """
        for s in self._stages:
            if s.id == stage_id:                               # ID 匹配
                return s.name
        return "未知阶段"

    def _get_stage_index(self, stage_id: str) -> int:
        """根据阶段 ID 获取该阶段在阶段列表中的索引位置。

        Args:
            stage_id: 阶段的唯一标识符。

        Returns:
            int: 索引位置（从 0 开始）；未找到返回 -1。
        """
        for i, s in enumerate(self._stages):
            if s.id == stage_id:
                return i
        return -1

    # =========================================================================
    # 窗口居中
    # =========================================================================

    def _center_window(self):
        """将对话框相对于其父窗口居中显示。"""
        self.update_idletasks()                                # 等待组件尺寸计算完成
        w = self.winfo_width()
        h = self.winfo_height()
        pw = self.master.winfo_width()
        ph = self.master.winfo_height()
        px = self.master.winfo_rootx()
        py = self.master.winfo_rooty()
        x = px + (pw - w) // 2                                 # 居中 X
        y = py + (ph - h) // 2                                 # 居中 Y
        self.geometry(f"+{x}+{y}")

    # =========================================================================
    # 焦点管理（失焦自动关闭）
    # =========================================================================

    def _on_focus_out(self, event):
        """Tk 焦点离开事件处理：延迟检查焦点状态。

        如果正在打开子窗口（_opening_child 为 True），跳过检查防止误关。
        否则延迟 100ms 后检查焦点是否真的离开了整个对话框。
        """
        if self._opening_child:                                # 打开子窗口时跳过
            return
        self.after(100, self._check_focus)                     # 延迟检查

    def _check_focus(self):
        """延迟检查焦点：如果当前没有任何子组件持有焦点，则关闭窗口。

        使用异常捕获处理窗口已被销毁导致的 TclError。
        """
        try:
            if not self.focus_get():                           # 无组件持有焦点
                self.destroy()
        except Exception:
            self.destroy()                                     # 窗口已销毁则安全关闭


# =============================================================================
# show_detail_dialog -- 便捷函数
# =============================================================================

def show_detail_dialog(parent, project: Project,
                       stages: list[WorkflowStage],
                       logs: list[dict],
                       on_move=None,
                       all_projects: list = None) -> tuple | None:
    """显示项目详情对话框并以事件循环方式运行。

    与简单的 wait_window() 模式不同，此函数使用 while 循环持续 update()，
    这样可以支持 move 操作（通过回调处理但不关闭窗口）和 edit/delete 操作
    （关闭窗口并返回结果）。

    Args:
        parent: 父级窗口。
        project: 要查看的项目实体。
        stages: 流程阶段列表。
        logs: 操作日志列表。
        on_move: 阶段移动回调函数。签名应为 on_move(new_stage_id, dialog)。
                 移动阶段时调用此回调（通常由 MainWindow 提供，负责更新数据和刷新对话框），
                 不会关闭对话框。

    Returns:
        tuple | None:
            对于 edit 操作返回 ("edit", form_data_dict)；
            对于 delete 操作返回 ("delete", None)；
            用户直接关闭窗口返回 None。
    """
    dialog = DetailDialog(parent, project, stages, logs, all_projects)

    # 事件循环：持续 update 直到窗口被关闭
    while dialog.winfo_exists():
        dialog.update()                                       # 处理所有待处理的 Tk 事件
        if dialog.result:                                     # 用户触发了操作
            action, data = dialog.result                      # 解包操作类型和数据
            dialog.result = None                              # 立即清空，防止重复处理
            if action == "move" and on_move:
                # 移动操作：通过回调处理（不关闭窗口，由 on_move 负责更新数据和刷新）
                on_move(data, dialog)
            else:
                # 编辑 / 删除操作：关闭窗口并返回结果
                dialog.destroy()
                return (action, data)
        try:
            dialog.update_idletasks()                         # 处理空闲任务
        except Exception:
            break                                             # 窗口已销毁则退出循环

    return None  # 窗口被直接关闭，无操作
