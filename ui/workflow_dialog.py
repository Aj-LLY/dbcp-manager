"""
流程阶段编辑对话框模块 -- 等保测评进度管理系统

本模块提供等保测评流程阶段的配置管理界面，包含两个对话框类：
  1. WorkflowDialog -- 主对话框，以 Treeview 表格展示所有流程阶段，支持增删改查和排序。
  2. StageEditDialog -- 子对话框，用于添加或编辑单个阶段的名称、颜色和列宽。

流程阶段在系统看板中从左到右按顺序显示，阶段之间的排序关系通过 order 字段维护。

外部使用 WorkflowDialog 时，只需传入当前阶段列表，确认后通过 result 属性获取更新后的列表。
"""

# =============================================================================
# 标准库导入
# =============================================================================
import tkinter as tk            # Tkinter GUI 库：构建桌面应用窗口和组件
from tkinter import ttk, messagebox, colorchooser  # ttk 增强组件 | messagebox 弹窗 | colorchooser 系统颜色选择器

# =============================================================================
# 项目内部模块导入
# =============================================================================
from models.workflow import WorkflowStage   # WorkflowStage 数据模型：表示一个流程阶段实体
from utils.config import Config            # 全局配置：字体族、字号、默认工作流阶段等常量
from utils.helpers import bordered_entry   # 辅助函数：创建带灰色外边框的输入框
from ui.widget_base import center_window, make_button_bar  # 公共 UI 组件


# =============================================================================
# WorkflowDialog -- 流程阶段编辑主对话框
# =============================================================================

class WorkflowDialog(tk.Toplevel):
    """流程阶段编辑对话框。

    以模态顶层窗口形式展示所有流程阶段，使用 Treeview 表格组件实现列表展示。
    支持以下操作：
      - 添加新阶段（弹出 StageEditDialog 收集名称和颜色）
      - 编辑选中阶段（修改名称、颜色和列宽）
      - 删除选中阶段（至少保留一个阶段）
      - 上移 / 下移调整阶段排序
      - 重置为系统默认流程配置
      - 保存当前配置并返回结果

    窗口布局：
      - 顶部：标题 + 使用说明文字
      - 中部：Treeview 表格（名称 / 颜色 / 列宽 三列）+ 滚动条
      - 中部下方：操作按钮行（添加、编辑、删除、上移、下移）
      - 底部：分隔线 + 按钮栏（重置默认 / 取消 / 保存）
      - 快捷键：双击 Treeview 行 → 编辑该阶段

    Attributes:
        result: list[dict] | None
            用户确认保存后为阶段字典列表（每个元素为 WorkflowStage.to_dict() 的输出），
            取消时为 None。
    """

    def __init__(self, parent, stages: list[WorkflowStage]):
        """初始化流程阶段编辑对话框。

        Args:
            parent: 父级窗口。
            stages: 当前的流程阶段列表。内部会拷贝一份以避免直接修改原列表。
        """
        # 调用父类 Tk.Toplevel 构造器，创建独立顶层窗口
        super().__init__(parent)
        self.title("编辑流程配置")                         # 设置对话框标题
        self.result = None                                 # 初始化结果（None 表示用户取消）
        self._stages = list(stages)                        # 深拷贝阶段列表，避免修改外部引用

        # ---- 按顺序执行初始化步骤 ----
        self._setup_window()     # ① 配置窗口基本属性
        self._build_ui()         # ② 构建 UI 布局
        self._refresh_list()     # ③ 填充 Treeview 数据
        center_window(self)       # ④ 窗口相对于父窗口居中
        self.grab_set()          # ⑤ 设为模态窗口

    def _setup_window(self):
        """配置对话框窗口的基本属性。

        设置初始大小 580×550（加宽加高以容纳新增列宽列），
        允许调整大小，最小尺寸 450×400，白色背景。
        """
        self.geometry("580x550")         # 初始窗口大小：宽580px，高550px
        self.resizable(True, True)       # 允许水平和垂直方向调整窗口大小
        self.minsize(450, 400)           # 最小尺寸：宽450px，高400px
        self.configure(bg="#ffffff")     # 窗口背景色为白色

    def _build_ui(self):
        """构建对话框的完整 UI 布局。

        组件层次（从上到下）：
            main [Frame, 主容器]
              ├── 标题 [Label] "流程阶段配置"
              ├── 使用说明 [Label] 灰色提示文字
              ├── list_frame [Frame]
              │     ├── Treeview (name / color / width 三列) + Scrollbar
              ├── btn_frame [Frame]
              │     └── op_frame [Frame] 操作按钮：添加 / 编辑 / 删除 / 上移 / 下移
              ├── sep [Frame] 分隔线
              └── bottom_bar [Frame] 底部按钮：重置默认(左) / 取消(右) / 保存(右)

        表格列定义：
          - name: 阶段名称（左对齐，宽度200）
          - color: 标识颜色（居中，宽度80），行背景色使用此颜色值
          - width: 列宽像素值（居中，宽度80，空值显示默认值）
        """
        # 主容器 Frame，20/18 内边距
        main = tk.Frame(self, bg="#ffffff", padx=22, pady=18)
        main.pack(fill=tk.BOTH, expand=True)               # 双向填充，占用整个窗口

        # ---- 标题行 ----
        tk.Label(main, text="流程阶段配置",
                 bg="#ffffff", fg="#2c3e50",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_HEADER, "bold"),
                 ).pack(anchor="w", pady=(0, 10))

        # ---- 使用说明文字 ----
        tk.Label(main,
                 text="配置等保测评的各个流程阶段。阶段将在看板中从左到右按顺序显示。",
                 bg="#ffffff", fg="#7f8c8d", wraplength=500,  # wraplength 自动换行宽度
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 justify="left",                             # 文本左对齐
                 ).pack(anchor="w", pady=(0, 10))

        # ---- 阶段列表区域（Treeview 表格 + 滚动条）----
        list_frame = tk.Frame(main, bg="#ffffff")
        list_frame.pack(fill=tk.BOTH, expand=True)          # 双向填充，可扩展占据主空间

        # 定义三列：名称、颜色、列宽
        columns = ("name", "color", "width")
        self._tree = ttk.Treeview(
            list_frame, columns=columns, show="headings",    # show="headings" 只显示表头，不显示树形图标列
            height=8, selectmode="browse",                  # 8行可见高度，单选模式
        )
        # 设置表头标题和锚点
        self._tree.heading("name", text="阶段名称", anchor="w")
        self._tree.heading("color", text="颜色", anchor="center")
        self._tree.heading("width", text="列宽(px)", anchor="center")
        # 设置列宽和内对齐方式
        self._tree.column("name", width=200, anchor="w")
        self._tree.column("color", width=80, anchor="center")
        self._tree.column("width", width=80, anchor="center")

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Treeview 填充左侧

        # 垂直滚动条，与 Treeview 联动
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                  command=self._tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)            # 滚动条在右侧，垂直填充
        self._tree.configure(yscrollcommand=scrollbar.set)   # 双向绑定

        # ---- 操作按钮行 ----
        btn_frame = tk.Frame(main, bg="#ffffff")
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        op_frame = tk.Frame(btn_frame, bg="#ffffff")        # 操作按钮内层容器
        op_frame.pack(side=tk.LEFT)

        # "添加阶段" -- 蓝色背景，点击弹出 StageEditDialog 收集新阶段信息
        self._btn_add = tk.Button(
            op_frame, text="\u2795 添加阶段", command=self._add_stage,
            bg="#3498db", fg="white", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=10, pady=4,
        )
        self._btn_add.pack(side=tk.LEFT, padx=(0, 5))

        # "编辑" -- 深色背景，编辑当前选中的阶段
        self._btn_edit = tk.Button(
            op_frame, text="\u270f\ufe0f 编辑", command=self._edit_stage,
            bg="#2c3e50", fg="white", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=10, pady=4,
        )
        self._btn_edit.pack(side=tk.LEFT, padx=(0, 5))

        # "删除" -- 红色背景，删除当前选中的阶段
        self._btn_delete = tk.Button(
            op_frame, text="\U0001f5d1\ufe0f 删除", command=self._delete_stage,
            bg="#e74c3c", fg="white", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=10, pady=4,
        )
        self._btn_delete.pack(side=tk.LEFT, padx=(0, 5))

        # "上移" -- 浅灰背景，将选中阶段与上一个阶段交换位置
        self._btn_up = tk.Button(
            op_frame, text="\u2b06\ufe0f 上移", command=self._move_up,
            bg="#ecf0f1", fg="#2c3e50", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=10, pady=4,
        )
        self._btn_up.pack(side=tk.LEFT, padx=(0, 5))

        # "下移" -- 浅灰背景，将选中阶段与下一个阶段交换位置
        self._btn_down = tk.Button(
            op_frame, text="\u2b07\ufe0f 下移", command=self._move_down,
            bg="#ecf0f1", fg="#2c3e50", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=10, pady=4,
        )
        self._btn_down.pack(side=tk.LEFT, padx=(0, 5))

        # ---- 分隔线 ----
        sep = tk.Frame(main, bg="#d0d5dd", height=1)        # 1px 灰色水平分隔线
        sep.pack(fill=tk.X, pady=(10, 0))

        # ---- 底部按钮栏 ----
        bottom_bar = tk.Frame(main, bg="#f0f2f5")
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        # "重置默认" -- 橙色背景，恢复系统默认流程阶段配置
        tk.Button(
            bottom_bar, text="重置默认", command=self._reset_default,
            bg="#f39c12", fg="white", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=12, pady=5,
        ).pack(side=tk.LEFT)

        # "取消" -- 白色背景灰色边框，关闭对话框不保存
        tk.Button(
            bottom_bar, text="取消", command=self.destroy,
            bg="#ffffff", fg="#2c3e50", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=20, pady=5,
            highlightbackground="#d0d5dd", highlightthickness=1,  # 灰色细边框
        ).pack(side=tk.RIGHT, padx=(6, 0))

        # "保存" -- 蓝色背景白色文字，确认并保存所有阶段配置
        tk.Button(
            bottom_bar, text="保存", bg="#3498db", fg="white", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL, "bold"),
            relief="flat", padx=20, pady=5,
            command=self._on_confirm,                        # 触发确认保存逻辑
        ).pack(side=tk.RIGHT)

        # 双击 Treeview 行直接打开编辑对话框
        self._tree.bind("<Double-1>", lambda e: self._edit_stage())

    # =========================================================================
    # Treeview 列表操作
    # =========================================================================

    def _refresh_list(self):
        """刷新 Treeview 中的阶段列表显示。

        操作步骤：
          1. 删除 Treeview 中的所有现有行。
          2. 遍历 _stages 列表，为每个阶段创建对应行。
          3. 行的 iid（标识符）使用阶段的 id，以便后续通过选中行查找阶段。
          4. 使用 tag_configure 将颜色值设置为行背景色，实现可视化颜色标识。
          5. 列宽列：如果阶段未设置 column_width 则显示 Config.COLUMN_WIDTH 默认值。
          6. 调用 update_idletasks 强制刷新显示。
        """
        # 清空所有现有行
        for item in self._tree.get_children():
            self._tree.delete(item)

        # 遍历阶段列表，逐行插入
        for stage in self._stages:
            # 列宽显示值：有自定义则用自定义值，否则使用 Config 默认值
            width_display = str(stage.column_width) if stage.column_width else str(Config.COLUMN_WIDTH)
            # 插入行：以 stage.id 作为行标识符(iid)，方便后续回溯阶段对象
            self._tree.insert("", tk.END, iid=stage.id,
                              values=(stage.name, stage.color, width_display),
                              tags=(stage.color,))                    # 用颜色值作为 tag，用于设置行背景
            # 配置 tag 样式：将颜色设置为行背景色
            self._tree.tag_configure(stage.color, background=stage.color)

        # 强制刷新 Treeview 显示（确保 UI 立即更新）
        self._tree.update_idletasks()

    def _get_selected_stage(self) -> WorkflowStage | None:
        """获取当前在 Treeview 中选中的流程阶段对象。

        通过 Treeview 的 selection() 获取选中行的 iid（即阶段 ID），
        然后在 _stages 列表中查找匹配的 WorkflowStage 实例。

        Returns:
            WorkflowStage | None: 选中的阶段对象；无选中返回 None。
        """
        selection = self._tree.selection()                  # 获取当前选中行 ID 列表
        if not selection:
            return None
        stage_id = selection[0]                             # 取第一个选中行（单选模式）
        for s in self._stages:
            if s.id == stage_id:                            # 按阶段 ID 查找
                return s
        return None

    def _get_selected_index(self) -> int:
        """获取当前选中阶段在 Treeview 中的视觉索引位置。

        Returns:
            int: 索引位置（从 0 开始）；无选中返回 -1。
        """
        sel = self._tree.selection()
        if not sel:
            return -1
        all_items = self._tree.get_children()               # 获取所有行 ID 的有序列表
        return all_items.index(sel[0])                      # 查找选中行在列表中的索引位置

    # =========================================================================
    # 阶段增删改操作
    # =========================================================================

    def _add_stage(self):
        """添加新阶段。

        弹出 StageEditDialog 子对话框让用户输入新阶段的名称和颜色，
        确认后创建一个新的 WorkflowStage 对象（order 值为当前最大 order + 1），
        添加到阶段列表末尾并刷新 Treeview 显示。
        """
        dialog = StageEditDialog(self, title="添加阶段")    # 打开添加阶段的子对话框
        self.wait_window(dialog)                            # 阻塞等待子对话框关闭
        if dialog.result:                                   # 用户点击了确认（result 非空）
            # 计算新阶段的排序值：当前最大 order + 1
            max_order = max((s.order for s in self._stages), default=-1)
            new_stage = WorkflowStage(
                name=dialog.result["name"],                  # 阶段名称
                color=dialog.result["color"],                # 标识颜色
                order=max_order + 1,                         # 排序序号
                column_width=dialog.result.get("column_width"),  # 列宽（可能为 None 表示用默认值）
            )
            self._stages.append(new_stage)                   # 添加到列表末尾
            self._refresh_list()                             # 刷新 Treeview 显示

    def _edit_stage(self):
        """编辑当前选中阶段的名称和颜色。

        获取 Treeview 中当前选中的阶段，弹出预填现有值（名称、颜色、列宽）
        的 StageEditDialog。用户确认后更新阶段对象属性并刷新显示。
        """
        stage = self._get_selected_stage()                   # 获取选中的阶段对象
        if not stage:
            messagebox.showinfo("提示", "请先选择要编辑的阶段", parent=self)
            return

        # 打开编辑对话框，预填当前名称、颜色和列宽
        dialog = StageEditDialog(self, title="编辑阶段",
                                 name=stage.name, color=stage.color,
                                 column_width=stage.column_width)
        self.wait_window(dialog)                             # 阻塞等待
        if dialog.result:                                    # 用户确认
            stage.name = dialog.result["name"]               # 更新阶段名称
            stage.color = dialog.result["color"]             # 更新标识颜色
            stage.column_width = dialog.result.get("column_width")  # 更新列宽
            self._refresh_list()                             # 刷新显示

    def _delete_stage(self):
        """删除当前选中的流程阶段。

        约束条件：至少需要保留一个流程阶段，防止删光。
        删除前弹出二次确认对话框，确认后移除阶段并重新编号所有阶段的 order 值。

        通过 Treeview 选中行的 iid（等于阶段 ID）直接定位阶段对象，
        比索引方式更可靠（避免列表和 Treeview 同步问题）。
        """
        # 守护条件：至少保留一个阶段
        if len(self._stages) <= 1:
            messagebox.showwarning("提示", "至少需要保留一个流程阶段", parent=self)
            return

        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在列表中点击选择要删除的阶段", parent=self)
            return

        # 通过 iid（阶段 ID）在 _stages 中查找目标阶段
        stage_id = sel[0]
        target = None
        for s in self._stages:
            if s.id == stage_id:
                target = s
                break

        if target is None:
            return

        # 二次确认对话框
        if messagebox.askyesno("确认删除",
                               f"确定要删除阶段\u300c{target.name}\u300d吗？",
                               parent=self):
            self._stages.remove(target)                      # 从列表中移除该阶段
            # 重新编号所有阶段的 order 值（保持顺序一致）
            for i, s in enumerate(self._stages):
                s.order = i
            self._refresh_list()                             # 刷新显示（同时清除选中状态）

    # =========================================================================
    # 排序操作
    # =========================================================================

    def _move_up(self):
        """将当前选中阶段上移一位（与上一个阶段交换位置）。

        操作步骤：
          1. 获取选中阶段在列表中的索引。
          2. 如果已是首个阶段（idx <= 0），直接返回。
          3. 在 _stages 列表中交换当前阶段和前一阶段的位置。
          4. 更新两个阶段的 order 值。
          5. 刷新 Treeview 并恢复选中状态到移动后的行。
        """
        idx = self._get_selected_index()                     # 获取当前选中索引
        if idx <= 0:                                         # 已是第一个，无法上移
            return
        # 交换两个阶段在列表中的位置（Python 元组交换）
        self._stages[idx], self._stages[idx - 1] = \
            self._stages[idx - 1], self._stages[idx]
        # 同步更新 order 值
        self._stages[idx].order = idx
        self._stages[idx - 1].order = idx - 1
        self._refresh_list()                                 # 刷新显示
        # 恢复选中状态到上移后的阶段行
        children = self._tree.get_children()
        if idx - 1 < len(children):
            self._tree.selection_set(children[idx - 1])

    def _move_down(self):
        """将当前选中阶段下移一位（与下一个阶段交换位置）。

        操作逻辑与 _move_up 对称：检查是否为最后一个阶段，
        与下一个阶段交换位置，更新 order 值，刷新并恢复选中。
        """
        idx = self._get_selected_index()
        if idx < 0 or idx >= len(self._stages) - 1:          # 已是最后一个，无法下移
            return
        # 交换当前阶段和下一阶段的位置
        self._stages[idx], self._stages[idx + 1] = \
            self._stages[idx + 1], self._stages[idx]
        # 同步更新 order 值
        self._stages[idx].order = idx
        self._stages[idx + 1].order = idx + 1
        self._refresh_list()                                 # 刷新显示
        # 恢复选中状态到下移后的阶段行
        children = self._tree.get_children()
        if idx + 1 < len(children):
            self._tree.selection_set(children[idx + 1])

    # =========================================================================
    # 重置与保存
    # =========================================================================

    def _reset_default(self):
        """重置为系统默认的流程阶段配置。

        二次确认后，从 Config.DEFAULT_WORKFLOW_STAGES 重新创建阶段列表，
        覆盖当前自定义的阶段配置。使用浅拷贝（s.copy()）避免后续操作
        影响 Config 中的默认值引用。
        """
        if messagebox.askyesno("确认重置",
                               "确定要重置为默认流程配置吗？\n"
                               "当前自定义的阶段将被覆盖。",
                               parent=self):
            # 重新创建默认阶段列表（每个阶段字典做浅拷贝，防止引用污染）
            self._stages = [
                WorkflowStage.from_dict(s.copy())
                for s in Config.get_default_workflow_stages()
            ]
            self._refresh_list()                             # 刷新 Treeview 显示

    def _on_confirm(self):
        """确认保存：验证后将阶段列表序列化到 self.result 并关闭窗口。

        验证规则：至少需要保留一个流程阶段。
        保存前将所有阶段的 order 值按列表位置重新编号，确保一致性。
        """
        if not self._stages:
            messagebox.showwarning("提示", "至少需要保留一个流程阶段", parent=self)
            return

        # 按当前列表位置重新编号所有阶段的 order 值
        for i, s in enumerate(self._stages):
            s.order = i

        # 将所有阶段序列化为字典列表存到 result
        self.result = [s.to_dict() for s in self._stages]
        self.destroy()  # 关闭对话框

    # =========================================================================
    # 窗口居中
    # =========================================================================



# =============================================================================
# StageEditDialog -- 单个阶段添加/编辑子对话框
# =============================================================================

class StageEditDialog(tk.Toplevel):
    """单个阶段的添加/编辑子对话框。

    用于新增阶段或编辑现有阶段的名称和颜色，提供以下功能：
      - 阶段名称输入框
      - 颜色选择器（系统颜色选择器 + 预设颜色块快速选择）
      - 列宽输入（可选，留空使用默认值 220px）
      - 键盘快捷键：Enter 确认，Esc 取消

    Attributes:
        result: dict | None
            用户确认后为 {"name": str, "color": str, "column_width": int|None}，
            取消时为 None。
    """

    def __init__(self, parent, title: str = "编辑阶段",
                 name: str = "", color: str = "#3498db",
                 column_width: int = None):
        """初始化阶段编辑子对话框。

        Args:
            parent: 父级窗口（WorkflowDialog 实例）。
            title: 对话框标题。
            name: 初始阶段名称（编辑模式预填）。
            color: 初始颜色值（编辑模式预填），默认蓝色 #3498db。
            column_width: 初始列宽（编辑模式预填），None 表示使用默认值。
        """
        # 调用父类 Tk.Toplevel 构造器
        super().__init__(parent)
        self.title(title)                                    # 设置窗口标题
        self.result = None                                   # 初始化结果

        # 配置窗口基本属性
        self.geometry("400x340")                             # 窗口大小：400×340
        self.minsize(340, 300)                               # 最小尺寸
        self.resizable(True, True)                           # 允许调整大小
        self.configure(bg="#ffffff")                         # 白色背景
        self.grab_set()                                      # 设为模态

        # 主容器 Frame
        main = tk.Frame(self, bg="#ffffff", padx=15, pady=15)
        main.pack(fill=tk.BOTH, expand=True)

        # ---- 阶段名称输入 ----
        tk.Label(main, text="阶段名称", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        self._name_var = tk.StringVar(value=name)            # 绑定名称的 StringVar，初始值为传入 name
        _, name_outer = bordered_entry(main, textvariable=self._name_var, width=40)
        name_outer.pack(fill=tk.X, pady=(2, 8))

        # ---- 标识颜色选择 ----
        tk.Label(main, text="标识颜色", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        color_frame = tk.Frame(main, bg="#ffffff")           # 颜色选择行容器
        color_frame.pack(fill=tk.X, pady=(2, 8))

        self._color_var = tk.StringVar(value=color)          # 绑定当前颜色值的 StringVar
        # 颜色预览块 -- 显示当前选中的颜色，实线边框
        self._color_preview = tk.Label(
            color_frame, text="   ", bg=color, width=4,
            relief="solid", borderwidth=1,
        )
        self._color_preview.pack(side=tk.LEFT, padx=(0, 8))

        # "选择颜色" 按钮 -- 打开系统颜色选择器
        tk.Button(color_frame, text="选择颜色", command=self._pick_color,
                  bg="#ecf0f1", relief="flat", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  padx=8, pady=3,
                  ).pack(side=tk.LEFT)

        # ---- 预设颜色块（快速选择）----
        preset_colors = [
            "#3498db", "#2ecc71", "#e67e22", "#e74c3c",
            "#9b59b6", "#1abc9c", "#f39c12", "#95a5a6",
            "#34495e", "#e91e63",
        ]
        preset_frame = tk.Frame(main, bg="#ffffff")
        preset_frame.pack(fill=tk.X, pady=(0, 8))
        for c in preset_colors:
            # 每个预设颜色为可点击的小色块 Label
            btn = tk.Label(preset_frame, text=" ", bg=c, width=2, height=1,
                           relief="solid", borderwidth=1, cursor="hand2")
            btn.pack(side=tk.LEFT, padx=1)
            # 绑定点击事件，lambda 闭包捕获当前颜色 c
            btn.bind("<Button-1>",
                     lambda e, clr=c: self._set_color(clr))

        # ---- 列宽输入 ----
        tk.Label(main, text="列宽（像素，留空使用默认220）", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        # 有自定义列宽则显示，为空则显示空字符串
        width_val = str(column_width) if column_width else ""
        self._width_var = tk.StringVar(value=width_val)      # 绑定列宽的 StringVar
        _, width_outer = bordered_entry(main, textvariable=self._width_var, width=40)
        width_outer.pack(fill=tk.X, pady=(2, 8))

        # ---- 底部固定按钮栏 ----
        btn_inner = make_button_bar(self)

        # "取消" -- 白色背景灰色边框
        tk.Button(btn_inner, text="取消", command=self.destroy,
                  bg="#ffffff", fg="#2c3e50", relief="flat", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  padx=18, pady=5,
                  highlightbackground="#d0d5dd", highlightthickness=1,
                  activebackground="#f0f2f5",
                  ).pack(side=tk.RIGHT, padx=(8, 0))

        # "确认" -- 蓝色背景白色文字
        tk.Button(btn_inner, text="确认", command=self._on_confirm,
                  bg="#3498db", fg="white", relief="flat", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  padx=18, pady=5,
                  activebackground="#2980b9",
                  ).pack(side=tk.RIGHT)

        # ---- 键盘快捷键绑定 ----
        self.bind("<Return>", lambda e: self._on_confirm())   # Enter 键 → 确认
        self.bind("<Escape>", lambda e: self.destroy())       # Esc 键 → 取消

        self._center(parent)                                  # 窗口居中于父窗口

    # =========================================================================
    # 颜色选择
    # =========================================================================

    def _pick_color(self):
        """打开系统颜色选择器对话框。

        使用 tkinter.colorchooser.askcolor 让用户自由选择任意颜色。
        选中后调用 _set_color 更新颜色变量和预览块。
        askcolor 返回 (RGB元组, 十六进制字符串) 或 (None, None)。
        """
        color = colorchooser.askcolor(
            initialcolor=self._color_var.get(),              # 初始颜色为当前选中值
            title="选择颜色",
            parent=self,
        )
        if color[1]:                                         # color[1] 为十六进制颜色字符串
            self._set_color(color[1])

    def _set_color(self, color: str):
        """设置颜色值并同步更新颜色预览块。

        Args:
            color: 十六进制颜色字符串（如 "#3498db"）。
        """
        self._color_var.set(color)                           # 更新 StringVar 变量值
        self._color_preview.configure(bg=color)              # 更新预览块的背景色

    # =========================================================================
    # 确认与验证
    # =========================================================================

    def _on_confirm(self):
        """确认按钮处理：验证阶段名称非空，保存结果并关闭。

        验证规则：阶段名称去除首尾空格后不能为空。
        保存结果为一个包含 name、color、column_width 的字典。
        """
        name = self._name_var.get().strip()                  # 获取名称并去空格
        if not name:
            messagebox.showwarning("提示", "阶段名称不能为空", parent=self)
            return

        self.result = {
            "name": name,                                    # 阶段名称
            "color": self._color_var.get(),                  # 标识颜色（十六进制）
            "column_width": self._parse_width(),             # 列宽（None 表示使用默认）
        }
        self.destroy()  # 关闭对话框

    def _parse_width(self):
        """解析列宽输入值。

        空字符串返回 None（表示使用默认列宽），
        非空时尝试转换为整数，正数有效，非正数返回 None。

        Returns:
            int | None: 列宽像素值，或 None（使用默认）。
        """
        val = self._width_var.get().strip()
        if not val:
            return None
        try:
            w = int(val)
            return w if w > 0 else None                      # 正数有效，≤0 视为无效使用默认
        except ValueError:
            return None

    # =========================================================================
    # 窗口居中
    # =========================================================================

    def _center(self, parent):
        """将子对话框居中于父窗口（WorkflowDialog）。

        Args:
            parent: 父窗口实例。
        """
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        x = px + (pw - w) // 2                               # 计算居中 X
        y = py + (ph - h) // 2                               # 计算居中 Y
        self.geometry(f"+{x}+{y}")
