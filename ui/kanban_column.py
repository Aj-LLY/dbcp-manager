"""
看板列模块 - 表示流程中的一个阶段列

本模块实现单列看板组件（KanbanColumn），每个列对应等保测评流程中的一个阶段。
每列包含以下子区域：
  1. 列标题栏（Header） - 显示阶段名称（左侧）+ 项目计数（右侧），背景色为阶段颜色
  2. 卡片可滚动区域 - Canvas + Scrollbar 实现垂直滚动，容纳该阶段的所有项目卡片
  3. 右侧拖拽手柄 - 4px 宽的拖拽条，支持鼠标拖拽调整列宽

核心功能：
  - 卡片管理：add_card / remove_card / clear_cards / find_card_by_project_id
  - 单选逻辑：select_card / deselect_all（列内同时只有一张卡片被选中）
  - 列宽调整：拖拽手柄实时调整列宽，释放后通知外部保存
  - 滚动支持：列内卡片超出可视区域时启用垂直滚动
  - 空白区域点击：取消所有卡片选中状态

架构层次：
  KanbanBoard（看板容器）
    └── KanbanColumn（本模块 - 单列）
          ├── Header Frame（列标题：阶段名称 + 计数）
          ├── Canvas（卡片滚动区域）
          │     └── cards_frame（卡片容器 Frame）
          │           └── ProjectCard（项目卡片）...
          └── Resize Grip（列宽拖拽手柄）

技术要点：
  - CardArea 使用 Canvas 滚动容器确保卡片多时不撑爆列
  - 列内卡片按列表顺序 pack，支持 top/bottom 插入控制
  - 拖拽手柄使用 <Button-1> / <B1-Motion> / <ButtonRelease-1> 三阶段事件
"""

# =============================================================================
# 导入区
# =============================================================================

import tkinter as tk  # Python 标准 GUI 库，提供 Frame、Canvas、Scrollbar 等组件

# ---- 模型层 ----
from models.project import Project  # 项目实体类：包含名称、编号、截止日期、阶段归属等字段
from models.workflow import WorkflowStage  # 流程阶段实体类：包含 ID、名称、颜色、列宽等属性

# ---- 视图层 ----
from ui.project_card import ProjectCard  # 项目卡片组件：展示单个项目的摘要信息和操作按钮

# ---- 工具层 ----
from utils.config import Config  # 全局配置类：提供列宽默认值、字体样式、背景色等 UI 常量


class KanbanColumn(tk.Frame):
    """看板列组件 - 继承自 tk.Frame

    每个 KanbanColumn 代表流程中的一个阶段（如"项目启动"、"方案设计"等），
    内部包含该阶段下所有项目卡片的列表，支持垂直滚动浏览。

    Attributes:
        stage (WorkflowStage): 关联的流程阶段实体（包含 ID、名称、颜色、列宽等）
        cards (list[ProjectCard]): 列内所有卡片组件的列表
        on_card_click: 卡片单击回调 -> 通知 KanbanBoard 处理选中逻辑
        on_card_double_click: 卡片双击回调 -> 通知 KanbanBoard 打开编辑
        on_column_click: 列空白区域点击回调 -> 取消所有选中
        on_resize: 列宽拖拽完成回调 -> 通知 KanbanBoard 保存宽度
        _col_w (int): 当前列的实际宽度（像素），初始取阶段配置值或默认值
        _resizing (bool): 是否正在进行拖拽调整宽度操作
    """

    def __init__(self, parent, stage: WorkflowStage, **kwargs):
        """初始化看板列

        创建列标题、卡片滚动区域和拖拽手柄三个子区域，
        并设置列宽（优先使用阶段自定义值，否则使用默认配置）。

        Args:
            parent: 父级容器（KanbanBoard 中的 columns_container Frame）
            stage: 流程阶段实体对象，提供阶段名称、颜色、列宽等信息
            **kwargs: 传递给父类 tk.Frame 的额外关键字参数
        """
        # 调用父类构造方法，设置列背景色和 1px 灰色边框
        super().__init__(parent, bg=Config.COLUMN_BG,  # 列背景色（浅灰）
                         highlightbackground="#c0c4cc",  # 边框颜色（中灰）
                         highlightthickness=1,  # 边框宽度 1px
                         **kwargs)

        # ---- 公共属性 ----
        self.stage = stage  # 保存关联的流程阶段实体对象
        self.cards: list[ProjectCard] = []  # 初始化列内卡片列表（类型标注，存储 ProjectCard 实例）

        # ---- 回调函数指针（由 KanbanBoard 在创建列后设置） ----
        self.on_card_click = None  # 卡片单击回调
        self.on_card_double_click = None  # 卡片双击回调
        self.on_column_click = None  # 列空白区域点击回调
        self.on_resize = None  # 列宽拖拽完成回调 -> (column, new_width)

        # ---- 列宽相关属性 ----
        # 列宽取值优先级：阶段自定义值 > 系统默认值
        self._col_w = self.stage.column_width or Config.COLUMN_WIDTH  # 当前列宽（整数）
        self._resize_start_x = 0  # 拖拽起始位置的屏幕 X 坐标（用于计算位移量）
        self._resize_start_w = 0  # 拖拽起始时的列宽（用于计算新宽度）
        self._resizing = False  # 是否正在拖拽调整宽度（防止误触发）

        # ---- 构建列的三个子区域 ----
        self._build_header()  # 1. 列标题栏（阶段名称 + 项目计数）
        self._build_cards_area()  # 2. 卡片可滚动区域（Canvas + Scrollbar）
        self._build_resize_grip()  # 3. 右侧拖拽手柄（4px 宽拖拽条）

        # 固定列宽（含滚动条 + 边距约 22px）
        self.configure(width=self._col_w + 22)

    # ==================================================================================
    # UI 构建 - 三个子区域
    # ==================================================================================

    def _build_header(self):
        """构建列标题栏

        标题栏使用阶段对应的颜色作为背景，布局：
          - 左侧：阶段名称标签（白色粗体文字）
          - 右侧：项目计数标签（白色文字，默认 "0"）

        标题栏固定高度 36px，禁止子组件撑开。
        """
        header = tk.Frame(self, bg=self.stage.color, height=36)  # 标题栏 Frame，阶段颜色背景，36px 高
        header.pack(fill=tk.X, padx=0, pady=0)  # 水平方向填充整个列宽度
        header.pack_propagate(False)  # 禁止子组件影响 Frame 尺寸（锁定 36px 高度）

        # --- 阶段名称标签（左侧） ---
        self._title_label = tk.Label(
            header, text=self.stage.name,  # 显示阶段名称（如"项目启动"）
            bg=self.stage.color, fg="white",  # 背景色与标题栏一致，白色文字
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),  # 粗体样式
        )
        self._title_label.pack(side=tk.LEFT, padx=10)  # 左侧放置，水平 10px 内边距

        # --- 项目计数标签（右侧） ---
        self._count_label = tk.Label(
            header, text="0",  # 初始计数为 0
            bg=self.stage.color, fg="white",  # 背景色与标题栏一致，白色文字
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),  # 小号字体
        )
        self._count_label.pack(side=tk.RIGHT, padx=10)  # 右侧放置，水平 10px 内边距

    def _build_cards_area(self):
        """构建卡片可滚动区域

        使用 Canvas + Frame + Scrollbar 标准组合实现垂直滚动：
          - Canvas：滚动容器画布，固定宽度与列宽一致
          - Scrollbar：垂直滚动条，控制 Canvas 的 yview
          - cards_frame：卡片容器 Frame，实际容纳所有 ProjectCard

        滚动机制：
          - cards_frame 的 Configure 事件自动更新 Canvas 的 scrollregion
          - 鼠标滚轮绑定到 Canvas 和 cards_frame 实现列内翻页
          - 空白区域点击绑定到 Canvas 和 cards_frame 实现取消选中
        """
        # --- 创建 Canvas 画布（滚动容器） ---
        self._canvas = tk.Canvas(
            self, bg=Config.COLUMN_BG,  # 列背景色
            highlightthickness=0,  # 无高亮边框
            width=self._col_w,  # 画布宽度与列宽一致
            height=Config.CARD_MIN_HEIGHT + 20,  # 最小高度（至少容纳一张卡片 + 边距）
        )

        # --- 创建垂直滚动条 ---
        self._scrollbar = tk.Scrollbar(
            self, orient=tk.VERTICAL,  # 垂直方向
            command=self._canvas.yview,  # 绑定到 Canvas 的 Y 轴视图控制
        )

        # --- 创建卡片容器 Frame（放置在 Canvas 内部） ---
        self._cards_frame = tk.Frame(self._canvas, bg=Config.COLUMN_BG)

        # 监听卡片容器大小变化，自动更新 Canvas 滚动区域
        self._cards_frame.bind("<Configure>",
                               lambda e: self._canvas.configure(
                                   scrollregion=self._canvas.bbox("all")))  # bbox("all") 获取所有内容边界

        # 在 Canvas 中创建窗口对象（嵌入卡片容器）
        # width 设置为 _col_w - 20，为右侧滚动条留出 20px 空间
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._cards_frame, anchor="nw",  # 左上角锚定
            width=self._col_w - 20,  # 窗口宽度 = 列宽 - 滚动条空间
        )

        # 配置 Canvas 与滚动条的双向联动
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        # --- 布局：滚动条在右侧，Canvas 填充剩余空间 ---
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  # 滚动条右侧，垂直填充
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Canvas 填充剩余

        # --- 事件绑定 ---
        self.bind("<Configure>", self._on_column_resize)  # 列 Frame 大小变化 -> 调整 Canvas 内窗口宽度
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)  # Canvas 上的滚轮事件
        self._cards_frame.bind("<MouseWheel>", self._on_mousewheel)  # 卡片容器上的滚轮事件
        self._canvas.bind("<Button-1>", self._on_bg_click)  # Canvas 空白区域点击
        self._cards_frame.bind("<Button-1>", self._on_bg_click)  # 卡片容器空白区域点击

    def _build_resize_grip(self):
        """构建右侧列宽拖拽手柄

        手柄是一个 4px 宽的 Frame，背景色为灰色，鼠标悬停时显示左右箭头光标。
        通过三阶段拖拽事件实现列宽调整：
          1. <Button-1>（按下）  -> 记录起始位置和宽度
          2. <B1-Motion>（移动） -> 实时计算并应用新宽度（最小 120px）
          3. <ButtonRelease-1>（释放） -> 保存最终宽度并通知外部
        """
        self._grip = tk.Frame(self, bg="#c0c4cc", width=4,  # 4px 宽，灰色背景
                              cursor="sb_h_double_arrow")  # 左右双箭头光标提示可拖拽
        self._grip.pack(side=tk.RIGHT, fill=tk.Y, padx=0, pady=0)  # 右侧垂直填充

        # 绑定拖拽三阶段事件
        self._grip.bind("<Button-1>", self._on_grip_press)  # 按下 -> 开始拖拽
        self._grip.bind("<B1-Motion>", self._on_grip_drag)  # 移动 -> 实时调整
        self._grip.bind("<ButtonRelease-1>", self._on_grip_release)  # 释放 -> 保存结果

    # ==================================================================================
    # 列宽拖拽事件处理
    # ==================================================================================

    def _on_grip_press(self, event):
        """拖拽手柄按下事件 - 记录起始位置和宽度，进入拖拽模式

        Args:
            event: Tkinter 的 Button-1 事件对象（event.x_root 为屏幕绝对 X 坐标）
        """
        self._resizing = True  # 标记进入拖拽模式
        self._resize_start_x = event.x_root  # 记录起始屏幕 X 坐标（绝对值）
        self._resize_start_w = self._col_w  # 记录拖拽开始时的列宽
        self._grip.configure(bg="#3498db")  # 手柄高亮（蓝色），提示用户正在拖拽

    def _on_grip_drag(self, event):
        """拖拽手柄移动事件 - 实时计算并应用新列宽

        计算公式：新宽度 = 起始宽度 + (当前鼠标X - 起始X)
        最小宽度限制为 120px，防止列过窄导致内容无法显示。

        Args:
            event: Tkinter 的 B1-Motion 事件对象
        """
        if not self._resizing:  # 非拖拽模式，忽略
            return
        dx = event.x_root - self._resize_start_x  # 计算鼠标水平位移量（像素）
        new_w = max(120, self._resize_start_w + dx)  # 新宽度 = 起始宽 + 位移量，下限 120px
        self._apply_width(new_w)  # 应用新宽度到所有相关组件

    def _on_grip_release(self, event):
        """拖拽手柄释放事件 - 保存最终宽度并退出拖拽模式

        释放后执行：
          1. 退出拖拽模式
          2. 恢复手柄颜色
          3. 将新宽度同步到 stage 模型的 column_width 属性
          4. 通知外部（KanbanBoard -> MainWindow）持久化保存

        Args:
            event: Tkinter 的 ButtonRelease-1 事件对象
        """
        if not self._resizing:  # 非拖拽模式，忽略
            return
        self._resizing = False  # 退出拖拽模式
        self._grip.configure(bg="#c0c4cc")  # 恢复手柄默认灰色
        # 将新宽度同步回阶段模型
        self.stage.column_width = self._col_w
        # 通知外部保存（最终由 MainWindow 调用 WorkflowService 持久化）
        if self.on_resize:
            self.on_resize(self, self._col_w)

    def _apply_width(self, new_w):
        """将新列宽应用到所有相关组件

        同时更新：
          - self 的宽度（含 22px 滚动条/边距）
          - Canvas 画布宽度
          - Canvas 内部窗口（cards_frame）宽度（减 20px 留滚动条空间）

        Args:
            new_w: 新的列内容宽度（不含滚动条和边距，单位：像素）
        """
        self._col_w = new_w  # 更新内部宽度变量
        self.configure(width=new_w + 22)  # 列 Frame 宽度 = 内容宽 + 滚动条/边距
        self._canvas.configure(width=new_w)  # Canvas 宽度 = 内容宽
        self._canvas.itemconfig(self._canvas_window, width=new_w - 20)  # 内部窗口宽度（留滚动条空间）

    def _on_column_resize(self, event):
        """列 Frame 大小变化时同步调整 Canvas 内部窗口宽度

        当列 Frame 被 pack 布局调整宽度（如窗口缩放、其他列宽拖拽影响）时，
        同步更新 Canvas 内部 cards_frame 窗口的宽度。

        Args:
            event: Tkinter 的 Configure 事件对象（event.width 为新宽度）
        """
        new_width = event.width - 22  # 减去滚动条和边距 = 内容可用宽度
        if new_width > 50:  # 最小宽度保护，避免太窄
            self._canvas.itemconfig(self._canvas_window, width=new_width)  # 更新内部窗口宽度

    # ==================================================================================
    # 滚动与点击事件
    # ==================================================================================

    def _on_mousewheel(self, event):
        """列内鼠标滚轮上下翻页

        仅在内容超出可见区域时才响应滚轮事件。
        当列内卡片较少、未超出视口时，滚轮事件不触发（避免无意义滚动）。

        Args:
            event: Tkinter 的 MouseWheel 事件对象（event.delta 为滚轮增量）
        """
        if self._cards_frame.winfo_height() <= self._canvas.winfo_height():
            return  # 内容高度未超出 Canvas，不需要滚动
        # event.delta / 120：标准化滚轮增量（正=向上），取负号调整方向
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_bg_click(self, event):
        """点击列空白区域取消所有卡片选中

        当用户点击列中没有卡片的空白区域时触发。

        Args:
            event: Tkinter 的 Button-1 事件对象
        """
        if self.on_column_click:  # 回调已设置（防御性检查）
            self.on_column_click(self)

    # ==================================================================================
    # 卡片管理 - 增删改查
    # ==================================================================================

    def add_card(self, project: Project, position: str = "bottom",
                 last_stage_id: str = None) -> ProjectCard:
        card = ProjectCard(self._cards_frame, project, last_stage_id=last_stage_id)
        card.on_click = self.on_card_click
        card.on_double_click = self.on_card_double_click
        card.pack(fill=tk.X, padx=4, pady=2, ipady=2)

        if position == "top":
            self.cards.insert(0, card)  # 插入到列表索引 0（最顶部位置）
        else:  # 底部追加
            self.cards.append(card)  # 追加到列表末尾

        # 按 cards 列表顺序重新调整所有卡片的视觉层叠顺序
        # 确保置顶的卡片在视觉上也处于最上方
        for i, c in enumerate(self.cards):
            if i == 0:  # 第一张卡片
                # before = 第二张卡片（如果存在），否则 before = None（在最顶部）
                c.pack_configure(before=self.cards[1] if len(self.cards) > 1 else None)
            else:  # 后续卡片
                # after = 前一张卡片（确保顺序与列表一致）
                c.pack_configure(after=self.cards[i - 1])

        self._update_count()  # 更新列标题中的项目计数显示
        return card  # 返回新创建的卡片引用

    def remove_card(self, card: ProjectCard):
        """从列中移除指定卡片

        执行两步清理：
          1. 从 cards 列表中移除（Python 层面）
          2. 销毁 Tkinter 组件（UI 层面，释放内存和屏幕空间）
          3. 更新计数显示

        Args:
            card: 要移除的 ProjectCard 实例
        """
        if card in self.cards:  # 防御性检查：确保卡片确实在此列中
            self.cards.remove(card)  # 从列表中移除引用
            card.destroy()  # 销毁 Tkinter 组件（释放 GDI 资源和内存）
            self._update_count()  # 更新列标题计数

    def clear_cards(self):
        """清空列中的所有卡片组件

        遍历销毁所有卡片并清空列表。
        通常在 load_stages()（全量重建看板）前调用。
        使用切片副本 [:] 遍历，避免在迭代过程中修改列表引发 RuntimeError。
        """
        for card in self.cards[:]:  # 遍历 cards 列表的副本（不影响原列表的遍历）
            card.destroy()  # 逐一销毁卡片组件
        self.cards.clear()  # 清空列表（移除所有引用）
        self._update_count()  # 更新计数为 0

    # ==================================================================================
    # 选择状态管理
    # ==================================================================================

    def select_card(self, card: ProjectCard):
        """选中指定卡片，同时取消列内其他卡片的选择状态

        实现列内的单选逻辑：同一列中同时只有一张卡片处于选中状态。

        Args:
            card: 要选中的 ProjectCard 实例
        """
        for c in self.cards:  # 遍历列内所有卡片
            c.set_selected(c is card)  # 仅目标卡片设为 True，其他全部设为 False

    def deselect_all(self):
        """取消列中所有卡片的选中状态

        通常在以下场景调用：
          - 用户点击列空白区域
          - 用户点击另一个列中的卡片
        """
        for c in self.cards:  # 遍历所有卡片
            c.set_selected(False)  # 每张卡片取消选中

    # ==================================================================================
    # 查询方法
    # ==================================================================================

    def find_card_by_project_id(self, project_id: str) -> ProjectCard | None:
        """根据项目 ID 在列中查找对应的卡片

        通常用于 refresh() 时恢复之前的选中状态。

        Args:
            project_id: 项目的唯一标识符（UUID 字符串）

        Returns:
            ProjectCard | None: 找到的卡片实例，未找到则返回 None
        """
        for c in self.cards:  # 遍历列内所有卡片
            ids = [p.id for p in (c.projects or [c.project])]
            if project_id in ids:
                return c
        return None  # 未找到

    # ==================================================================================
    # 内部辅助方法
    # ==================================================================================

    def _update_count(self):
        """更新列标题中的项目计数显示

        将当前 cards 列表的长度同步到标题栏右侧的计数标签中。
        每次卡片增删后自动调用，确保计数实时准确。
        """
        self._count_label.configure(text=str(len(self.cards)))  # 设置计数字符串
