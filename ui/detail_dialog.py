"""
项目详情对话框 - 查看和编辑项目完整信息

双击卡片弹出，展示项目详细信息，支持：
- 查看项目基本信息
- 快速编辑项目属性
- 查看该项目的历史操作日志
- 阶段移动（上一阶段/下一阶段）
- 删除项目（带二次确认）
"""

import tkinter as tk  # 导入Tkinter GUI库，用于构建桌面应用界面组件
from tkinter import messagebox  # 导入messagebox，用于显示警告/确认弹窗
from models.project import Project  # 导入Project模型类，表示一个等保测评项目实体
from models.workflow import WorkflowStage  # 导入WorkflowStage模型类，表示一个流程阶段实体
from ui.project_dialog import show_project_dialog  # 导入项目编辑对话框便捷函数
from utils.config import Config  # 导入Config配置类，获取字体等UI配置常量
from utils.helpers import days_until_deadline  # 导入辅助函数：计算距离截止日期的剩余天数


class DetailDialog(tk.Toplevel):
    """项目详情对话框 - 继承自tk.Toplevel

    展示项目的完整信息，包括基本信息、备注、操作日志记录。
    提供编辑、删除和阶段移动等操作入口。
    """

    def __init__(self, parent, project: Project,
                 stages: list[WorkflowStage],
                 project_logs: list[dict]):
        """初始化详情对话框

        Args:
            parent: 父级窗口
            project: 要展示的项目实体
            stages: 流程阶段列表（用于阶段移动和编辑时提供可选项）
            project_logs: 该项目的操作日志列表（按时间排序）
        """
        super().__init__(parent)
        self.title(f"项目详情 - {project.name}")  # 标题中包含项目名称
        self._project = project  # 保存项目引用
        self._stages = stages  # 保存阶段列表引用
        self._logs = project_logs  # 保存日志列表引用

        self.result = None  # 结果数据：("edit", data) / ("delete", None) / ("move", stage_id) / None

        self._setup_window()  # 配置窗口属性
        self._build_ui()  # 构建详情界面
        self._center_window()  # 窗口居中
        self.grab_set()  # 设置为模态窗口

    def _setup_window(self):
        """配置窗口属性"""
        self.geometry("500x500")  # 固定大小 500x500
        self.resizable(False, False)  # 不可调整大小
        self.configure(bg="#ffffff")  # 白色背景

    def _build_ui(self):
        """构建详情界面的UI布局

        从上到下包含：
        - 标题行（项目名称）
        - 信息区域（公司名、系统名、备案号、阶段、截止日期、创建时间、更新时间）
        - 备注内容
        - 操作日志摘要（最近5条）
        - 操作按钮（阶段移动、编辑、删除、关闭）
        """
        main = tk.Frame(self, bg="#ffffff", padx=24, pady=18)  # 主容器
        main.pack(fill=tk.BOTH, expand=True)

        # 标题行 - 显示项目名称
        header = tk.Frame(main, bg="#ffffff")
        header.pack(fill=tk.X, pady=(0, 15))  # 水平填充，下方15px间距

        tk.Label(header, text=self._project.name,
                 bg="#ffffff", fg="#2c3e50",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_HEADER, "bold"),
                 wraplength=400, justify="left",  # 自动换行，左对齐
                 ).pack(anchor="w")

        # 信息区域 - 浅灰背景的卡片式信息块
        info_frame = tk.Frame(main, bg="#f8f9fa", padx=12, pady=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # 逐行添加项目信息字段（标签: 值）
        # 公司名称
        self._add_info_row(info_frame, "公司名称",
                           self._project.company_name or "-")
        # 系统名称
        self._add_info_row(info_frame, "系统名称",
                           self._project.system_name or "-")
        # 证书编号
        self._add_info_row(info_frame, "证书编号",
                           self._project.cert_number or "未备案")
        # 当前阶段
        stage_name = self._get_stage_name(self._project.stage_id)  # 通过stage_id查找阶段名称
        self._add_info_row(info_frame, "当前阶段", stage_name)

        # 截止日期 - 包含剩余天数提示
        deadline = self._project.deadline or "未设置"
        days_left = days_until_deadline(self._project.deadline) if self._project.deadline else None
        if days_left is not None:
            if days_left < 0:
                deadline += f"  ⚠️ 已超期 {abs(days_left)} 天"
            elif days_left <= Config.DEADLINE_WARNING_DAYS:
                deadline += f"  ⚡ 剩余 {days_left} 天"  # 临近截止警告
            else:
                deadline += f"  剩余 {days_left} 天"
        self._add_info_row(info_frame, "截止日期", deadline)

        # 创建时间
        self._add_info_row(info_frame, "创建时间", self._project.created_at)

        # 最后更新时间
        self._add_info_row(info_frame, "最后更新", self._project.updated_at)

        # 备注信息 - 只读多行文本框
        notes = self._project.notes or "无"
        tk.Label(main, text="备注信息", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                 fg="#2c3e50").pack(anchor="w", pady=(5, 2))  # 标签
        notes_text = tk.Text(main, height=4, wrap="word",
                             font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                             bg="#f8f9fa", relief="flat", borderwidth=1)
        notes_text.insert("1.0", notes)  # 插入备注内容
        notes_text.configure(state="disabled")  # 设为只读（禁止编辑）
        notes_text.pack(fill=tk.X)

        # 操作日志摘要 - 显示最近5条操作记录
        tk.Label(main, text="操作记录（最近5条）", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                 fg="#2c3e50").pack(anchor="w", pady=(10, 2))

        log_frame = tk.Frame(main, bg="#f8f9fa")  # 日志列表容器
        log_frame.pack(fill=tk.X, pady=(0, 5))

        recent_logs = self._logs[:5]  # 取最近5条日志
        if recent_logs:
            for log in recent_logs:
                # 格式化为 "时间 | 操作类型 | 描述" 的单行文本
                log_text = f"{log.get('timestamp', '')} | {log.get('action', '')} | {log.get('detail', '')}"
                if len(log_text) > 65:
                    log_text = log_text[:64] + "\u2026"  # 超过65字符截断加省略号
                tk.Label(log_frame, text=log_text, bg="#f8f9fa",
                         font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                         fg="#7f8c8d", anchor="w", justify="left",
                         ).pack(fill=tk.X, pady=1, padx=8)
        else:
            tk.Label(log_frame, text="暂无操作记录", bg="#f8f9fa",
                     font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                     fg="#95a5a6").pack(pady=8)  # 无日志时的占位文字

        # 操作按钮区域
        btn_frame = tk.Frame(main, bg="#ffffff")
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        # 进度移动按钮 - 左箭头：移至上一阶段
        tk.Button(btn_frame, text="\u25c0 上一阶段", command=self._move_prev,
                  bg="#ecf0f1", fg="#2c3e50", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  relief="flat", padx=12, pady=5,
                  ).pack(side=tk.LEFT, padx=(0, 5))

        # 进度移动按钮 - 右箭头：移至下一阶段
        tk.Button(btn_frame, text="下一阶段 \u25b6", command=self._move_next,
                  bg="#ecf0f1", fg="#2c3e50", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  relief="flat", padx=12, pady=5,
                  ).pack(side=tk.LEFT)

        # 右侧操作按钮
        # 编辑按钮 - 蓝色
        tk.Button(btn_frame, text="编辑", command=self._edit_project,
                  bg="#3498db", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  relief="flat", padx=12, pady=5,
                  ).pack(side=tk.RIGHT, padx=(5, 0))

        # 删除项目按钮 - 红色（有二次确认）
        tk.Button(btn_frame, text="删除项目", command=self._delete_project,
                  bg="#e74c3c", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  relief="flat", padx=12, pady=5,
                  ).pack(side=tk.RIGHT)

        # 关闭按钮 - 灰色
        tk.Button(main, text="关闭", command=self.destroy,
                  bg="#ecf0f1", fg="#2c3e50", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                  relief="flat", padx=16, pady=4,
                  ).pack(pady=(10, 0))

    def _add_info_row(self, parent, label: str, value: str):
        """在信息区域添加一行 "标签: 值" 格式的信息

        Args:
            parent: 父容器Frame
            label: 信息字段标签名
            value: 信息字段值
        """
        row = tk.Frame(parent, bg="#f8f9fa")  # 行容器
        row.pack(fill=tk.X, pady=2)  # 水平填充，行间距2px
        # 标签列 - 右对齐，固定宽度10字符，灰色文字
        tk.Label(row, text=label + "\uff1a", bg="#f8f9fa",  # 全角冒号
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 fg="#7f8c8d", width=10, anchor="e",
                 ).pack(side=tk.LEFT)
        # 值列 - 左对齐，深色文字
        tk.Label(row, text=value, bg="#f8f9fa",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 fg="#2c3e50", anchor="w",
                 ).pack(side=tk.LEFT, padx=(5, 0))

    def _edit_project(self):
        """编辑项目按钮处理

        打开项目编辑对话框，编辑成功后保存结果到self.result
        并关闭详情窗口（外部MainWindow会捕获result并执行更新操作）。
        """
        result = show_project_dialog(
            self, "编辑项目", self._project, self._stages,
        )
        if result:  # 用户确认保存
            self.result = ("edit", result)  # 设置结果为编辑操作
            self.destroy()  # 关闭详情窗口

    def _delete_project(self):
        """删除项目按钮处理

        显示二次确认对话框，确认后设置result为删除操作并关闭窗口。
        """
        if messagebox.askyesno("确认删除",
                               f"确定要永久删除项目\u300c{self._project.name}\u300d吗？\n\n"
                               "此操作不可撤销！",
                               parent=self):
            self.result = ("delete", None)  # 设置结果为删除操作
            self.destroy()

    def _move_prev(self):
        """移到上一阶段按钮处理

        查找当前阶段在阶段列表中的索引，如果不在第一个位置，
        则设置result为移动到前一阶段的ID。
        """
        idx = self._get_stage_index(self._project.stage_id)
        if idx > 0:  # 不是第一个阶段
            self.result = ("move", self._stages[idx - 1].id)  # 移动到前一阶段
            self.destroy()
        else:
            messagebox.showinfo("提示", "已经是第一个阶段", parent=self)

    def _move_next(self):
        """移到下一阶段按钮处理

        查找当前阶段在阶段列表中的索引，如果不在最后一个位置，
        则设置result为移动到后一阶段的ID。
        """
        idx = self._get_stage_index(self._project.stage_id)
        if idx < len(self._stages) - 1:  # 不是最后一个阶段
            self.result = ("move", self._stages[idx + 1].id)  # 移动到后一阶段
            self.destroy()
        else:
            messagebox.showinfo("提示", "已经是最后一个阶段", parent=self)

    def _get_stage_name(self, stage_id: str) -> str:
        """根据阶段ID获取阶段名称

        Args:
            stage_id: 阶段的唯一标识符

        Returns:
            str: 阶段名称，找不到返回"未知阶段"
        """
        for s in self._stages:
            if s.id == stage_id:
                return s.name
        return "未知阶段"

    def _get_stage_index(self, stage_id: str) -> int:
        """根据阶段ID获取阶段在列表中的索引位置

        Args:
            stage_id: 阶段的唯一标识符

        Returns:
            int: 索引位置（从0开始），未找到返回-1
        """
        for i, s in enumerate(self._stages):
            if s.id == stage_id:
                return i
        return -1

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


def show_detail_dialog(parent, project: Project,
                       stages: list[WorkflowStage],
                       logs: list[dict]) -> tuple | None:
    """显示项目详情对话框的便捷函数

    创建DetailDialog实例并等待用户操作完成后返回结果。

    Args:
        parent: 父级窗口
        project: 项目实体
        stages: 流程阶段列表
        logs: 项目操作日志列表

    Returns:
        tuple | None: (action, data) 格式的结果元组，取消返回None
            action可能的值："edit"（编辑）, "delete"（删除）, "move"（移动阶段）
    """
    dialog = DetailDialog(parent, project, stages, logs)
    parent.wait_window(dialog)  # 阻塞等待对话框关闭
    return dialog.result
