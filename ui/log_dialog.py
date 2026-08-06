"""
操作日志查看对话框模块 -- 等保测评进度管理系统

本模块提供系统操作日志的查看和筛选界面，以模态对话框形式展示。
主要功能包括：
  - 以 Treeview 表格形式列出所有操作记录
  - 显示字段：时间、操作类型、操作描述、关联项目
  - 按关联项目名称进行筛选（下拉框选择）
  - 日志总数统计显示
  - 支持水平和垂直滚动，适应宽表格内容

日志列表默认为只读浏览，不提供编辑或删除功能。
外部使用者应通过 show_log_dialog() 便捷函数调用。
"""

# =============================================================================
# 标准库导入
# =============================================================================
import tkinter as tk            # Tkinter GUI 库：构建桌面应用窗口和组件
from tkinter import ttk         # ttk 增强组件：Treeview 表格、Combobox 下拉框等

# =============================================================================
# 项目内部模块导入
# =============================================================================
from utils.config import Config  # 全局配置：字体族、字号等 UI 常量


# =============================================================================
# LogDialog -- 操作日志查看模态对话框
# =============================================================================

class LogDialog(tk.Toplevel):
    """操作日志查看对话框。

    以模态顶层窗口形式展示所有系统操作日志。使用 Treeview 表格
    以列表形式呈现，支持按项目名称筛选和实时统计显示。

    窗口布局（从上到下）：
      - 标题行：左侧标题图标 + 右侧记录计数
      - 筛选栏：浅灰背景，包含项目筛选下拉框 + 刷新按钮
      - 日志表格：Treeview（4列：时间 / 操作类型 / 操作描述 / 关联项目）
        + 垂直滚动条 + 水平滚动条
      - 底部：关闭按钮（居中）

    表格列定义：
      - time（时间）：宽度 150px，左对齐
      - action（操作类型）：宽度 100px，居中
      - detail（操作描述）：宽度 400px，左对齐
      - project（关联项目）：宽度 180px，左对齐
      所有列设 stretch=False，确保溢出时触发水平滚动而非压缩列宽。

    Attributes:
        无公共属性。日志对话框仅做展示，关闭后无返回值。
    """

    def __init__(self, parent, logs: list[dict]):
        """初始化操作日志对话框。

        Args:
            parent: 父级窗口。
            logs: 操作日志列表。每个元素为 dict，预期包含以下键：
                timestamp（时间），action（操作类型），detail（操作描述），
                project_name（关联项目名称）。
        """
        # 调用父类 Tk.Toplevel 构造器
        super().__init__(parent)
        self.title("操作日志")                                 # 设置窗口标题
        self._logs = logs                                      # 保存日志列表引用

        # ---- 按顺序执行初始化步骤 ----
        self._setup_window()     # ① 配置窗口基本属性
        self._build_ui()         # ② 构建 UI 布局
        self._load_logs()        # ③ 初始加载日志到 Treeview
        self._center_window()    # ④ 窗口居中
        self.grab_set()          # ⑤ 设为模态窗口

    def _setup_window(self):
        """配置对话框窗口的基本属性。

        初始大小 780×520（加宽以适应 4 列表格），
        可调整大小，最小尺寸 600×400，白色背景。
        """
        self.geometry("780x520")         # 初始窗口大小
        self.resizable(True, True)       # 允许水平和垂直调整
        self.minsize(600, 400)           # 最小尺寸
        self.configure(bg="#ffffff")     # 白色背景

    def _build_ui(self):
        """构建日志对话框的完整 UI 布局。

        组件层次（从上到下）：
            main [Frame, 主容器]
              ├── header_frame [Frame]
              │     ├── 标题 Label "📜 操作日志" (LEFT)
              │     └── 记录计数 Label "共 N 条记录" (RIGHT)
              ├── filter_frame [Frame, 浅灰背景]
              │     ├── 筛选标签 "筛选项目："
              │     ├── 项目筛选 Combobox
              │     └── 刷新 [Button]
              ├── tree_frame [Frame]
              │     └── Treeview (4列) + VScrollbar + HScrollbar (grid 布局)
              └── 关闭 [Button, 底部居中]

        筛选下拉框自动从日志中提取所有唯一的项目名称作为选项，
        同时在列表顶部添加 "全部" 选项以取消筛选。
        """
        # 主容器 Frame
        main = tk.Frame(self, bg="#ffffff", padx=22, pady=18)
        main.pack(fill=tk.BOTH, expand=True)                   # 填充整个窗口

        # ---- 标题行：标题 + 记录计数 ----
        header_frame = tk.Frame(main, bg="#ffffff")
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # 左侧标题（带图标）
        tk.Label(header_frame, text="\U0001f4dc 操作日志",
                 bg="#ffffff", fg="#2c3e50",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_HEADER, "bold"),
                 ).pack(side=tk.LEFT)

        # 右侧记录计数标签（初始为空，加载后更新为"共 N 条记录"）
        self._count_label = tk.Label(
            header_frame, text="",
            bg="#ffffff", fg="#7f8c8d",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
        )
        self._count_label.pack(side=tk.RIGHT)

        # ---- 筛选栏 ----
        filter_frame = tk.Frame(main, bg="#f8f9fa")
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        # 筛选标签
        tk.Label(filter_frame, text="筛选项目：", bg="#f8f9fa",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 ).pack(side=tk.LEFT, padx=(8, 5))

        # 项目筛选下拉框：默认选中"全部"（不筛选）
        self._filter_var = tk.StringVar(value="全部")
        self._filter_combo = ttk.Combobox(
            filter_frame, textvariable=self._filter_var,
            state="readonly", width=30,                       # 只读，宽度30字符
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
        )
        self._filter_combo.pack(side=tk.LEFT, padx=(0, 5))
        # 用户选择筛选条件时，自动应用筛选刷新表格
        self._filter_combo.bind("<<ComboboxSelected>>",
                                lambda e: self._apply_filter())

        # 刷新按钮 -- 浅灰背景，重新加载日志数据并更新筛选下拉选项
        tk.Button(filter_frame, text="刷新", command=self._load_logs,
                  bg="#ecf0f1", relief="flat", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  padx=8).pack(side=tk.RIGHT, padx=(0, 8))

        # ---- 日志表格区域（Treeview + 双滚动条，grid 布局） ----
        tree_frame = tk.Frame(main, bg="#ffffff")
        tree_frame.pack(fill=tk.BOTH, expand=True)             # 双向填充，占据主空间
        tree_frame.grid_rowconfigure(0, weight=1)              # 行 0 可扩展
        tree_frame.grid_columnconfigure(0, weight=1)           # 列 0 可扩展

        # 定义四个列名
        columns = ("time", "action", "detail", "project")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",      # 只显示表头
            selectmode="browse",                               # 单选模式
        )
        # 设置各列的表头标题和内对齐方式
        self._tree.heading("time", text="时间", anchor="w")
        self._tree.heading("action", text="操作类型", anchor="center")
        self._tree.heading("detail", text="操作描述", anchor="w")
        self._tree.heading("project", text="关联项目", anchor="w")

        # 设置各列宽度（stretch=False 防止压缩，溢出时触发水平滚动）
        self._tree.column("time", width=140, anchor="w", stretch=False)
        self._tree.column("action", width=80, anchor="center", stretch=False)
        self._tree.column("detail", width=500, anchor="w", stretch=True)
        self._tree.column("project", width=160, anchor="w", stretch=False)
        print(f"[日志对话框] 列宽: time=140 action=80 detail=500(stretch) project=160", flush=True)
        print(f"[日志对话框] tree_frame grid: row0-weight={tree_frame.grid_rowconfigure(0)}, col0-weight={tree_frame.grid_columnconfigure(0)}", flush=True)

        # 创建垂直和水平滚动条
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                    command=self._tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL,
                                    command=self._tree.xview)
        self._tree.configure(yscrollcommand=scrollbar_y.set,
                             xscrollcommand=scrollbar_x.set)   # 与两个滚动条双向绑定

        # Grid 布局：Treeview 位于 (0,0)，垂直滚动条 (0,1)，水平滚动条 (1,0)
        # 网格布局优于 pack，可避免右下角交叉空白区域
        self._tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        # ---- 底部关闭按钮 ----
        tk.Button(main, text="关闭", command=self.destroy,
                  bg="#ecf0f1", fg="#2c3e50", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                  relief="flat", padx=20, pady=6,
                  ).pack(pady=(10, 0))

    # =========================================================================
    # 日志数据加载与筛选
    # =========================================================================

    def _load_logs(self):
        """加载日志数据并更新筛选下拉框选项。

        操作步骤：
          1. 保存当前筛选条件。
          2. 从日志数据中提取所有唯一的项目名称，构造下拉选项列表。
          3. 将选项列表设为 ["全部"] + 排序后的项目名称列表。
          4. 如果之前的筛选条件仍然有效则恢复，否则默认"全部"。
          5. 调用 _apply_filter() 刷新 Treeview 显示。
        """
        current_filter = self._filter_var.get()                # 保存当前筛选条件

        # 从日志列表中提取所有唯一的项目名称（使用 set 去重）
        project_names = set()
        for log in self._logs:
            if log.get("project_name"):
                project_names.add(log["project_name"])
        # 更新筛选下拉框选项："全部" + 按字母排序的项目名称列表
        self._filter_combo["values"] = ["全部"] + sorted(project_names)

        # 恢复之前的筛选条件（如果仍在新选项列表中有效）
        if current_filter and current_filter != "全部":
            self._filter_var.set(current_filter)
        else:
            self._filter_var.set("全部")                       # 默认不筛选

        self._apply_filter()                                   # 应用筛选并刷新表格

    def _apply_filter(self):
        """应用当前筛选条件并刷新 Treeview 显示。

        操作步骤：
          1. 清空 Treeview 中所有现有行。
          2. 根据筛选下拉框的值过滤日志列表。
          3. 将筛选后的日志逐行插入 Treeview。
          4. 更新记录计数标签。
        """
        # 清空所有现有行
        for item in self._tree.get_children():
            self._tree.delete(item)

        # 获取筛选条件值
        filter_name = self._filter_var.get()
        filtered_logs = self._logs                              # 默认不筛选（显示全部）
        if filter_name and filter_name != "全部":
            # 按关联项目名称筛选
            filtered_logs = [
                log for log in self._logs
                if log.get("project_name") == filter_name
            ]

        max_len = max((len(log.get("detail","")) for log in filtered_logs), default=0)
        print(f"[日志对话框] {len(filtered_logs)}条日志, 最长detail={max_len}字", flush=True)
        for log in filtered_logs:
            self._tree.insert("", tk.END, values=(
                log.get("timestamp", ""),                      # 时间列
                log.get("action", ""),                         # 操作类型列
                log.get("detail", ""),                         # 操作描述列
                log.get("project_name", ""),                   # 关联项目列
            ))

        # 更新记录计数标签
        self._count_label.configure(
            text=f"共 {len(filtered_logs)} 条记录"
        )

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


# =============================================================================
# show_log_dialog -- 便捷函数
# =============================================================================

def show_log_dialog(parent, logs: list[dict]):
    """显示操作日志对话框的便捷函数。

    创建 LogDialog 实例并以模态方式展示（阻塞父窗口交互），
    等待用户关闭对话框后返回。日志对话框仅用于查看，无返回值。

    Args:
        parent: 父级窗口。
        logs: 日志列表（dict 列表），每条日志需包含 timestamp、action、
              detail、project_name 等字段。
    """
    dialog = LogDialog(parent, logs)                           # 创建对话框实例
    parent.wait_window(dialog)                                 # 阻塞等待，直到对话框关闭
