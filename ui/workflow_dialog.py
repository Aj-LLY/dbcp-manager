"""
流程编辑对话框 - 配置等保测评的流程阶段

支持：
- 查看当前所有流程阶段
- 添加新阶段
- 编辑阶段名称和颜色
- 删除阶段（至少保留一个）
- 上移/下移调整阶段顺序
- 重置为默认流程配置
"""

import tkinter as tk  # 导入Tkinter GUI库，用于构建桌面应用界面组件
from tkinter import ttk, messagebox, colorchooser  # ttk提供增强组件，messagebox弹窗，colorchooser颜色选择器
from models.workflow import WorkflowStage  # 导入WorkflowStage模型类，表示一个流程阶段实体
from utils.config import Config  # 导入Config配置类，获取字体等UI配置常量
from utils.helpers import bordered_entry  # 导入辅助函数：创建带边框样式的输入框


class WorkflowDialog(tk.Toplevel):
    """流程阶段编辑对话框 - 继承自tk.Toplevel

    使用Treeview列表展示所有流程阶段，支持增删改查和排序操作。
    阶段将在看板中从左到右按顺序显示。
    """

    def __init__(self, parent, stages: list[WorkflowStage]):
        """初始化对话框

        Args:
            parent: 父级窗口
            stages: 当前的流程阶段列表
        """
        super().__init__(parent)  # 调用父类Toplevel初始化
        self.title("编辑流程配置")  # 设置窗口标题
        self.result = None  # 初始化结果数据（None表示用户取消）
        self._stages = list(stages)  # 复制阶段列表（避免修改原列表）

        self._setup_window()  # 配置窗口属性
        self._build_ui()  # 构建对话框UI布局
        self._refresh_list()  # 刷新Treeview中显示阶段列表
        self._center_window()  # 窗口居中
        self.grab_set()  # 设置为模态窗口

    def _setup_window(self):
        """配置窗口属性：大小、最小尺寸、可调整性和背景色"""
        self.geometry("580x550")  # 设置初始窗口大小（加宽加高以适应新增列宽列）
        self.resizable(True, True)  # 允许调整大小
        self.minsize(450, 400)  # 设置最小尺寸
        self.configure(bg="#ffffff")  # 白色背景

    def _build_ui(self):
        """构建流程阶段编辑对话框的UI布局

        包含：标题、说明文字、阶段列表面板、操作按钮、底部保存/取消按钮。
        阶段列表使用Treeview组件以表格形式展示。
        """
        main = tk.Frame(self, bg="#ffffff", padx=22, pady=18)  # 主容器
        main.pack(fill=tk.BOTH, expand=True)  # 填充整个窗口

        # 标题行
        tk.Label(main, text="流程阶段配置",
                 bg="#ffffff", fg="#2c3e50",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_HEADER, "bold"),
                 ).pack(anchor="w", pady=(0, 10))  # 左对齐，下方10px间距

        # 使用说明
        tk.Label(main,
                 text="配置等保测评的各个流程阶段。阶段将在看板中从左到右按顺序显示。",
                 bg="#ffffff", fg="#7f8c8d", wraplength=500,  # wraplength: 文字自动换行宽度500像素
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 justify="left",  # 左对齐
                 ).pack(anchor="w", pady=(0, 10))

        # 阶段列表区域
        list_frame = tk.Frame(main, bg="#ffffff")
        list_frame.pack(fill=tk.BOTH, expand=True)  # 双向填充，可扩展

        # Treeview表格 - 显示阶段列表（名称 + 颜色 + 列宽）
        columns = ("name", "color", "width")  # 定义表格列名
        self._tree = ttk.Treeview(
            list_frame, columns=columns, show="headings",  # show="headings"只显示表头，不显示树形图标列
            height=8, selectmode="browse",  # 8行可见，单选模式
        )
        self._tree.heading("name", text="阶段名称", anchor="w")  # 名称列表头，左对齐
        self._tree.heading("color", text="颜色", anchor="center")  # 颜色列表头，居中
        self._tree.heading("width", text="列宽(px)", anchor="center")  # 列宽表头，居中
        self._tree.column("name", width=200, anchor="w")  # 名称列宽200，左对齐
        self._tree.column("color", width=80, anchor="center")  # 颜色列宽80，居中
        self._tree.column("width", width=80, anchor="center")  # 列宽列宽80，居中

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Treeview填充左侧

        # 滚动条（垂直）
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                  command=self._tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  # 右侧垂直填充
        self._tree.configure(yscrollcommand=scrollbar.set)  # 与滚动条联动

        # 按钮区域
        btn_frame = tk.Frame(main, bg="#ffffff")
        btn_frame.pack(fill=tk.X, pady=(10, 0))  # 水平填充，上方10px间距

        # 操作按钮（左侧）
        op_frame = tk.Frame(btn_frame, bg="#ffffff")
        op_frame.pack(side=tk.LEFT)  # 左侧放置

        # 添加阶段按钮 - 蓝色
        self._btn_add = tk.Button(
            op_frame, text="➕ 添加阶段", command=self._add_stage,
            bg="#3498db", fg="white", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=10, pady=4,
        )
        self._btn_add.pack(side=tk.LEFT, padx=(0, 5))  # 左排列，右间距5px

        # 编辑阶段按钮 - 深色
        self._btn_edit = tk.Button(
            op_frame, text="✏️ 编辑", command=self._edit_stage,
            bg="#2c3e50", fg="white", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=10, pady=4,
        )
        self._btn_edit.pack(side=tk.LEFT, padx=(0, 5))

        # 删除阶段按钮 - 红色
        self._btn_delete = tk.Button(
            op_frame, text="🗑️ 删除", command=self._delete_stage,
            bg="#e74c3c", fg="white", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=10, pady=4,
        )
        self._btn_delete.pack(side=tk.LEFT, padx=(0, 5))

        # 排序按钮 - 上移
        self._btn_up = tk.Button(
            op_frame, text="⬆️ 上移", command=self._move_up,
            bg="#ecf0f1", fg="#2c3e50", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=10, pady=4,
        )
        self._btn_up.pack(side=tk.LEFT, padx=(0, 5))

        # 排序按钮 - 下移
        self._btn_down = tk.Button(
            op_frame, text="⬇️ 下移", command=self._move_down,
            bg="#ecf0f1", fg="#2c3e50", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=10, pady=4,
        )
        self._btn_down.pack(side=tk.LEFT, padx=(0, 5))

        # 底部操作栏（分隔线 + 保存/取消/重置按钮）
        sep = tk.Frame(main, bg="#d0d5dd", height=1)  # 灰色分隔线
        sep.pack(fill=tk.X, pady=(10, 0))

        bottom_bar = tk.Frame(main, bg="#f0f2f5")  # 底部按钮栏
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        # 重置默认按钮 - 橙色，恢复默认流程配置
        tk.Button(
            bottom_bar, text="重置默认", command=self._reset_default,
            bg="#f39c12", fg="white", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=12, pady=5,
        ).pack(side=tk.LEFT)  # 左侧放置

        # 取消按钮 - 白色，关闭对话框不保存
        tk.Button(
            bottom_bar, text="取消", command=self.destroy,
            bg="#ffffff", fg="#2c3e50", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=20, pady=5,
            highlightbackground="#d0d5dd", highlightthickness=1,  # 灰色边框
        ).pack(side=tk.RIGHT, padx=(6, 0))  # 右侧放置

        # 保存按钮 - 蓝色，确认保存流程配置
        tk.Button(
            bottom_bar, text="保存", bg="#3498db", fg="white", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL, "bold"),
            relief="flat", padx=20, pady=5,
            command=self._on_confirm,  # 触发确认保存逻辑
        ).pack(side=tk.RIGHT)  # 紧挨取消按钮左侧

        # 双击编辑 - 双击Treeview行直接打开编辑对话框
        self._tree.bind("<Double-1>", lambda e: self._edit_stage())

    def _refresh_list(self):
        """刷新Treeview中的阶段列表

        先清空所有行，再根据_stages列表重新填充。
        为每个阶段设置颜色标签，让Treeview行背景显示对应颜色。
        """
        for item in self._tree.get_children():  # 获取并删除所有现有行
            self._tree.delete(item)

        for stage in self._stages:
            # 插入新行，以阶段ID作为行标识符(iid)
            width_display = str(stage.column_width) if stage.column_width else str(Config.COLUMN_WIDTH)
            self._tree.insert("", tk.END, iid=stage.id,
                              values=(stage.name, stage.color, width_display),  # 显示名称、颜色和列宽
                              tags=(stage.color,))  # 用颜色值作为标签（用于设置行背景色）
            # 配置标签样式：将颜色值设置为行背景色
            self._tree.tag_configure(stage.color, background=stage.color)

        # 强制刷新 Treeview 显示（确保UI立即更新）
        self._tree.update_idletasks()

    def _get_selected_stage(self) -> WorkflowStage | None:
        """获取当前选中的阶段对象

        通过Treeview的选中行ID（即阶段ID）在_stages列表中查找匹配的阶段。

        Returns:
            WorkflowStage | None: 选中的阶段对象，无选中返回None
        """
        selection = self._tree.selection()  # 获取当前选中的行ID列表
        if not selection:
            return None
        stage_id = selection[0]  # 取第一个选中行的ID（单选模式）
        for s in self._stages:
            if s.id == stage_id:  # 匹配阶段ID
                return s
        return None

    def _get_selected_index(self) -> int:
        """获取当前选中阶段在Treeview列表中的视觉索引位置

        Returns:
            int: 索引位置（从0开始），无选中返回-1
        """
        sel = self._tree.selection()
        if not sel:
            return -1
        all_items = self._tree.get_children()  # 获取所有行的ID列表
        return all_items.index(sel[0])  # 查找选中行ID在列表中的位置

    def _add_stage(self):
        """添加新阶段

        打开StageEditDialog小对话框收集新阶段名称和颜色，
        自动计算order值为当前最大order+1，添加到列表末尾。
        """
        dialog = StageEditDialog(self, title="添加阶段")  # 打开添加阶段的编辑对话框
        if dialog.result:  # 用户点击确认
            max_order = max((s.order for s in self._stages), default=-1)  # 获取当前最大order值
            new_stage = WorkflowStage(
                name=dialog.result["name"],
                color=dialog.result["color"],
                order=max_order + 1,  # 新阶段的order = 最大order + 1
                column_width=dialog.result.get("column_width"),  # 列宽
            )
            self._stages.append(new_stage)  # 添加到阶段列表
            self._refresh_list()  # 刷新Treeview显示

    def _edit_stage(self):
        """编辑选中阶段的名称和颜色

        获取当前选中的阶段，打开编辑对话框进行修改。
        修改后直接更新阶段对象的属性并刷新显示。
        """
        stage = self._get_selected_stage()
        if not stage:
            messagebox.showinfo("提示", "请先选择要编辑的阶段", parent=self)
            return

        dialog = StageEditDialog(self, title="编辑阶段",
                                 name=stage.name, color=stage.color,
                                 column_width=stage.column_width)  # 预填现有名称、颜色和列宽
        if dialog.result:  # 用户点击确认
            stage.name = dialog.result["name"]  # 更新阶段名称
            stage.color = dialog.result["color"]  # 更新阶段颜色
            stage.column_width = dialog.result.get("column_width")  # 更新列宽
            self._refresh_list()  # 刷新显示

    def _delete_stage(self):
        """删除选中阶段

        限制条件：至少需要保留一个流程阶段。
        删除后重新编号所有阶段的order值，并清除Treeview选中状态。
        """
        if len(self._stages) <= 1:
            messagebox.showwarning("提示", "至少需要保留一个流程阶段", parent=self)
            return

        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在列表中点击选择要删除的阶段", parent=self)
            return

        # 通过 Treeview 的 iid 直接定位阶段
        stage_id = sel[0]  # Treeview的行ID即阶段ID
        target = None
        for s in self._stages:
            if s.id == stage_id:
                target = s
                break

        if target is None:
            return

        # 二次确认删除
        if messagebox.askyesno("确认删除",
                               f"确定要删除阶段「{target.name}」吗？",
                               parent=self):
            self._stages.remove(target)  # 从列表中移除
            for i, s in enumerate(self._stages):
                s.order = i  # 重新编号所有阶段的order值
            self._refresh_list()  # 刷新显示（同时清除了选中状态）

    def _move_up(self):
        """上移选中阶段（调整排序）

        将选中阶段与其前一个阶段交换位置，实现排序上升。
        同时更新两个阶段的order值。
        """
        idx = self._get_selected_index()  # 获取当前选中索引
        if idx <= 0:  # 已经是第一个，无法上移
            return
        # 交换两个阶段在列表中的位置
        self._stages[idx], self._stages[idx - 1] = \
            self._stages[idx - 1], self._stages[idx]
        # 更新order值
        self._stages[idx].order = idx
        self._stages[idx - 1].order = idx - 1
        self._refresh_list()  # 刷新显示
        # 恢复选中状态到上移后的阶段
        children = self._tree.get_children()
        if idx - 1 < len(children):
            self._tree.selection_set(children[idx - 1])

    def _move_down(self):
        """下移选中阶段（调整排序）

        将选中阶段与其后一个阶段交换位置，实现排序下降。
        """
        idx = self._get_selected_index()
        if idx < 0 or idx >= len(self._stages) - 1:  # 已经是最后一个，无法下移
            return
        # 交换两个阶段在列表中的位置
        self._stages[idx], self._stages[idx + 1] = \
            self._stages[idx + 1], self._stages[idx]
        # 更新order值
        self._stages[idx].order = idx
        self._stages[idx + 1].order = idx + 1
        self._refresh_list()  # 刷新显示
        children = self._tree.get_children()
        if idx + 1 < len(children):
            self._tree.selection_set(children[idx + 1])  # 恢复选中

    def _reset_default(self):
        """重置为默认流程配置

        二次确认后，从Config.DEFAULT_WORKFLOW_STAGES重新创建阶段列表，
        覆盖当前自定义的阶段配置。
        """
        if messagebox.askyesno("确认重置",
                               "确定要重置为默认流程配置吗？\n"
                               "当前自定义的阶段将被覆盖。",
                               parent=self):
            from utils.config import Config  # 局部导入Config（避免循环依赖）
            # 从默认配置创建新的阶段列表（使用深拷贝避免引用问题）
            self._stages = [
                WorkflowStage.from_dict(s.copy())
                for s in Config.DEFAULT_WORKFLOW_STAGES
            ]
            self._refresh_list()  # 刷新显示

    def _on_confirm(self):
        """确认保存流程配置

        验证至少有一个阶段，确保所有阶段的order值正确，
        将阶段列表序列化为字典列表存入result并关闭窗口。
        """
        if not self._stages:
            messagebox.showwarning("提示", "至少需要保留一个流程阶段", parent=self)
            return

        # 确保order值与列表顺序一致
        for i, s in enumerate(self._stages):
            s.order = i  # 按列表位置重新设置order

        self.result = [s.to_dict() for s in self._stages]  # 序列化所有阶段为字典列表
        self.destroy()  # 关闭对话框

    def _center_window(self):
        """窗口居中显示 - 相对于父窗口居中"""
        self.update_idletasks()  # 等待更新完成，获取准确尺寸
        w = self.winfo_width()
        h = self.winfo_height()
        pw = self.master.winfo_width()
        ph = self.master.winfo_height()
        px = self.master.winfo_rootx()  # 父窗口屏幕X坐标
        py = self.master.winfo_rooty()  # 父窗口屏幕Y坐标
        x = px + (pw - w) // 2  # 居中X
        y = py + (ph - h) // 2  # 居中Y
        self.geometry(f"+{x}+{y}")  # 设置窗口位置


class StageEditDialog(tk.Toplevel):
    """单个阶段的添加/编辑小对话框

    用于新增阶段或编辑现有阶段的名称和颜色。
    提供名称输入框、颜色选择器和预设颜色块。
    """

    def __init__(self, parent, title: str = "编辑阶段",
                 name: str = "", color: str = "#3498db",
                 column_width: int = None):
        """初始化阶段编辑对话框

        Args:
            parent: 父级窗口
            title: 对话框标题
            name: 初始阶段名称（编辑模式预填）
            color: 初始颜色值（编辑模式预填）
            column_width: 初始列宽（None表示使用默认值）
        """
        super().__init__(parent)  # 调用父类Toplevel初始化
        self.title(title)
        self.result = None  # 结果数据

        self.geometry("400x340")  # 窗口大小
        self.minsize(340, 300)  # 最小尺寸
        self.resizable(True, True)  # 允许调整大小
        self.configure(bg="#ffffff")
        self.grab_set()  # 模态

        main = tk.Frame(self, bg="#ffffff", padx=15, pady=15)  # 主容器
        main.pack(fill=tk.BOTH, expand=True)

        # 阶段名称输入
        tk.Label(main, text="阶段名称", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")  # 左对齐
        self._name_var = tk.StringVar(value=name)  # 绑定名称的StringVar，初始值为传入的name
        _, name_outer = bordered_entry(main, textvariable=self._name_var, width=40)
        name_outer.pack(fill=tk.X, pady=(2, 8))  # 水平填充

        # 标识颜色选择
        tk.Label(main, text="标识颜色", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        color_frame = tk.Frame(main, bg="#ffffff")  # 颜色选择行
        color_frame.pack(fill=tk.X, pady=(2, 8))

        self._color_var = tk.StringVar(value=color)  # 绑定颜色的StringVar
        # 颜色预览块 - 显示当前选中的颜色
        self._color_preview = tk.Label(
            color_frame, text="   ", bg=color, width=4,
            relief="solid", borderwidth=1,  # 实线边框
        )
        self._color_preview.pack(side=tk.LEFT, padx=(0, 8))

        # 自定义颜色选择按钮 - 打开系统颜色选择器
        tk.Button(color_frame, text="选择颜色", command=self._pick_color,
                  bg="#ecf0f1", relief="flat", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  padx=8, pady=3,
                  ).pack(side=tk.LEFT)

        # 预设颜色块 - 提供一组常用颜色供快速选择
        preset_colors = [
            "#3498db", "#2ecc71", "#e67e22", "#e74c3c",
            "#9b59b6", "#1abc9c", "#f39c12", "#95a5a6",
            "#34495e", "#e91e63",
        ]
        preset_frame = tk.Frame(main, bg="#ffffff")
        preset_frame.pack(fill=tk.X, pady=(0, 8))
        for c in preset_colors:
            # 每个预设颜色为一个可点击的Label
            btn = tk.Label(preset_frame, text=" ", bg=c, width=2, height=1,
                           relief="solid", borderwidth=1, cursor="hand2")
            btn.pack(side=tk.LEFT, padx=1)  # 水平排列，间距1px
            # 绑定点击事件，使用lambda闭包捕获当前颜色c
            btn.bind("<Button-1>",
                     lambda e, clr=c: self._set_color(clr))

        # 列宽输入
        tk.Label(main, text="列宽（像素，留空使用默认220）", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        width_val = str(column_width) if column_width else ""
        self._width_var = tk.StringVar(value=width_val)
        _, width_outer = bordered_entry(main, textvariable=self._width_var, width=40)
        width_outer.pack(fill=tk.X, pady=(2, 8))

        # 底部按钮（取消 + 确认）—— 固定在最底部
        btn_frame = tk.Frame(self, bg="#f0f2f5")
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(btn_frame, bg="#d0d5dd", height=1).pack(fill=tk.X)
        btn_inner = tk.Frame(btn_frame, bg="#f0f2f5")
        btn_inner.pack(fill=tk.X, padx=16, pady=8)
        tk.Button(btn_inner, text="取消", command=self.destroy,
                  bg="#ffffff", fg="#2c3e50", relief="flat", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  padx=18, pady=5,
                  highlightbackground="#d0d5dd", highlightthickness=1,
                  activebackground="#f0f2f5",
                  ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(btn_inner, text="确认", command=self._on_confirm,
                  bg="#3498db", fg="white", relief="flat", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  padx=18, pady=5,
                  activebackground="#2980b9",
                  ).pack(side=tk.RIGHT)

        # 键盘快捷键
        self.bind("<Return>", lambda e: self._on_confirm())  # 回车确认
        self.bind("<Escape>", lambda e: self.destroy())  # Esc取消

        self._center(parent)  # 居中于父窗口

    def _pick_color(self):
        """打开系统颜色选择器对话框

        使用tkinter.colorchooser让用户自由选择颜色。
        选择后更新颜色变量和预览块。
        """
        color = colorchooser.askcolor(
            initialcolor=self._color_var.get(),  # 初始颜色为当前值
            title="选择颜色",
            parent=self,
        )
        if color[1]:  # color返回(RGB元组, 十六进制字符串)，取颜色值
            self._set_color(color[1])  # 使用十六进制颜色字符串

    def _set_color(self, color: str):
        """设置颜色并更新预览块

        Args:
            color: 十六进制颜色字符串（如 "#3498db"）
        """
        self._color_var.set(color)  # 更新StringVar变量值
        self._color_preview.configure(bg=color)  # 更新预览块背景色

    def _on_confirm(self):
        """确认按钮处理：验证名称非空并保存结果"""
        name = self._name_var.get().strip()  # 获取并去除首尾空格
        if not name:
            messagebox.showwarning("提示", "阶段名称不能为空", parent=self)
            return
        self.result = {
            "name": name,
            "color": self._color_var.get(),
            "column_width": self._parse_width(),  # 解析列宽（None=使用默认）
        }
        self.destroy()  # 关闭对话框

    def _parse_width(self):
        """解析列宽输入值：空返回None（使用默认），非空返回整数值"""
        val = self._width_var.get().strip()
        if not val:
            return None
        try:
            w = int(val)
            return w if w > 0 else None  # 正数有效，非正数返回None
        except ValueError:
            return None

    def _center(self, parent):
        """居中于父窗口

        Args:
            parent: 父窗口（WorkflowDialog实例）
        """
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")
