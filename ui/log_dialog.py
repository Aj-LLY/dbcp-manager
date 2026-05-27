"""
操作日志查看对话框 - 展示系统所有操作记录

功能：
- 列表展示所有操作日志（时间倒序）
- 显示操作类型、描述、关联项目和时间
- 支持按项目筛选
- 显示日志总数统计
"""

import tkinter as tk  # 导入Tkinter GUI库，用于构建桌面应用界面组件
from tkinter import ttk  # 导入ttk增强组件（Treeview表格等）
from utils.config import Config  # 导入Config配置类，获取字体等UI配置常量


class LogDialog(tk.Toplevel):
    """操作日志查看对话框 - 继承自tk.Toplevel

    使用Treeview表格展示所有系统操作日志，支持按项目名称筛选。
    """

    def __init__(self, parent, logs: list[dict]):
        """初始化对话框

        Args:
            parent: 父级窗口
            logs: 操作日志列表（dict列表），每条日志包含：
                timestamp（时间），action（操作类型），detail（描述），project_name（关联项目）
        """
        super().__init__(parent)
        self.title("操作日志")  # 设置窗口标题
        self._logs = logs  # 保存日志列表

        self._setup_window()  # 配置窗口属性
        self._build_ui()  # 构建UI布局
        self._load_logs()  # 加载日志到Treeview
        self._center_window()  # 窗口居中
        self.grab_set()  # 设置为模态窗口

    def _setup_window(self):
        """配置窗口属性：大小、可调整性、背景色"""
        self.geometry("780x520")  # 初始窗口大小
        self.resizable(True, True)  # 允许用户调整大小
        self.minsize(600, 400)  # 设置最小尺寸
        self.configure(bg="#ffffff")  # 白色背景

    def _build_ui(self):
        """构建日志对话框的UI布局

        包含：
        - 标题行（标题 + 记录计数）
        - 筛选栏（按项目下拉筛选 + 刷新按钮）
        - 日志表格（Treeview：时间、操作类型、描述、关联项目）
        - 底部关闭按钮
        """
        main = tk.Frame(self, bg="#ffffff", padx=22, pady=18)
        main.pack(fill=tk.BOTH, expand=True)  # 填充整个窗口

        # 标题行
        header_frame = tk.Frame(main, bg="#ffffff")
        header_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(header_frame, text="📜 操作日志",
                 bg="#ffffff", fg="#2c3e50",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_HEADER, "bold"),
                 ).pack(side=tk.LEFT)  # 左侧标题

        # 记录计数标签 - 右侧显示"共N条记录"
        self._count_label = tk.Label(
            header_frame, text="",
            bg="#ffffff", fg="#7f8c8d",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
        )
        self._count_label.pack(side=tk.RIGHT)  # 右侧放置

        # 筛选栏 - 浅灰背景
        filter_frame = tk.Frame(main, bg="#f8f9fa")
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(filter_frame, text="筛选项目：", bg="#f8f9fa",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 ).pack(side=tk.LEFT, padx=(8, 5))  # 筛选标签

        # 项目筛选下拉框 - 包含"全部"和所有项目名称
        self._filter_var = tk.StringVar(value="全部")  # 默认"全部"（不筛选）
        self._filter_combo = ttk.Combobox(
            filter_frame, textvariable=self._filter_var,
            state="readonly", width=30,  # 只读下拉框
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
        )
        self._filter_combo.pack(side=tk.LEFT, padx=(0, 5))
        # 当用户选择筛选条件时，自动应用筛选
        self._filter_combo.bind("<<ComboboxSelected>>",
                                lambda e: self._apply_filter())

        # 刷新按钮
        tk.Button(filter_frame, text="刷新", command=self._load_logs,
                  bg="#ecf0f1", relief="flat", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  padx=8).pack(side=tk.RIGHT, padx=(0, 8))

        # 日志列表区域（Treeview表格 + 双滚动条）
        tree_frame = tk.Frame(main, bg="#ffffff")
        tree_frame.pack(fill=tk.BOTH, expand=True)  # 双向填充，占用主空间

        # 定义表格列
        columns = ("time", "action", "detail", "project")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",  # 只显示表头
            selectmode="browse",  # 单选模式
        )
        # 设置各列标题和锚点
        self._tree.heading("time", text="时间", anchor="w")
        self._tree.heading("action", text="操作类型", anchor="center")
        self._tree.heading("detail", text="操作描述", anchor="w")
        self._tree.heading("project", text="关联项目", anchor="w")

        # 设置各列宽度和对齐方式
        self._tree.column("time", width=150, anchor="w")
        self._tree.column("action", width=100, anchor="center")
        self._tree.column("detail", width=350, anchor="w")
        self._tree.column("project", width=150, anchor="w")

        # 创建垂直和水平滚动条
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                    command=self._tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL,
                                    command=self._tree.xview)
        # Treeview与滚动条联动
        self._tree.configure(yscrollcommand=scrollbar_y.set,
                             xscrollcommand=scrollbar_x.set)

        # 布局Treeview和滚动条
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Treeview填充左侧主区域
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)  # 垂直滚动条：右侧
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)  # 水平滚动条：底部

        # 关闭按钮 - 底部居中
        tk.Button(main, text="关闭", command=self.destroy,
                  bg="#ecf0f1", fg="#2c3e50", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                  relief="flat", padx=20, pady=6,
                  ).pack(pady=(10, 0))  # 上方10px间距

    def _load_logs(self):
        """加载日志到Treeview

        解析日志列表，提取所有项目名称更新筛选下拉框选项，
        然后应用当前筛选条件显示对应日志。
        """
        # 保存当前筛选条件
        current_filter = self._filter_var.get()

        # 更新筛选下拉列表 - 从日志中提取所有唯一的项目名称
        project_names = set()  # 使用集合去重
        for log in self._logs:
            if log.get("project_name"):
                project_names.add(log["project_name"])
        self._filter_combo["values"] = ["全部"] + sorted(project_names)  # "全部" + 排序后的项目名

        # 恢复之前的筛选条件（如果仍然有效）
        if current_filter and current_filter != "全部":
            self._filter_var.set(current_filter)
        else:
            self._filter_var.set("全部")  # 默认不筛选

        self._apply_filter()  # 应用筛选并显示

    def _apply_filter(self):
        """应用筛选条件并刷新Treeview显示

        根据筛选下拉框的选中值过滤日志列表，清空表格后重新填充。
        同时更新底部的记录计数标签。
        """
        # 清空表格中所有现有行
        for item in self._tree.get_children():
            self._tree.delete(item)

        # 获取筛选条件，筛选日志列表
        filter_name = self._filter_var.get()
        filtered_logs = self._logs  # 默认显示全部
        if filter_name and filter_name != "全部":
            # 按项目名称筛选
            filtered_logs = [
                log for log in self._logs
                if log.get("project_name") == filter_name
            ]

        # 逐个插入筛选后的日志到Treeview
        for log in filtered_logs:
            self._tree.insert("", tk.END, values=(  # tk.END表示追加到末尾
                log.get("timestamp", ""),  # 时间列
                log.get("action", ""),     # 操作类型列
                log.get("detail", ""),     # 描述列
                log.get("project_name", ""),  # 关联项目列
            ))

        # 更新记录计数标签
        self._count_label.configure(
            text=f"共 {len(filtered_logs)} 条记录"
        )

    def _center_window(self):
        """窗口居中显示"""
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        pw = self.master.winfo_width()
        ph = self.master.winfo_height()
        px = self.master.winfo_rootx()
        py = self.master.winfo_rooty()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")


def show_log_dialog(parent, logs: list[dict]):
    """显示操作日志对话框的便捷函数

    创建LogDialog实例并等待用户关闭。

    Args:
        parent: 父级窗口
        logs: 日志列表（dict列表）
    """
    dialog = LogDialog(parent, logs)
    parent.wait_window(dialog)  # 阻塞等待对话框关闭
    # 注意：此处不返回result，因为日志对话框仅是查看，无返回值
