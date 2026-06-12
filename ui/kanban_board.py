"""
看板容器模块 - 整个看板视图的顶层容器组件

本模块实现水平滚动的多列看板布局（KanbanBoard），核心职责：
  1. 管理所有 KanbanColumn 列组件的创建、排列和销毁
  2. 提供横向和纵向滚动支持（Canvas + 双 Scrollbar）
  3. 统一的卡片选中状态管理（全局单选模式）
  4. 卡片箭头按钮的阶段移动逻辑（前移/后移到相邻列）
  5. 鼠标滚轮支持（垂直滚动 + Shift+滚轮横向滚动）
  6. 列宽拖拽调整事件的转发和保存

架构层次：
  MainWindow（控制器）
    └── KanbanBoard（本模块 - 看板容器）
          ├── Canvas（滚动画布，支持双向滚动）
          │     └── columns_container（列容器 Frame）
          │           ├── KanbanColumn（列组件 - 每个流程阶段一列）
          │           │     ├── 列标题（Header：阶段名 + 计数）
          │           │     └── 卡片区（Canvas 滚动）
          │           │           └── ProjectCard（项目卡片）
          │           └── KanbanColumn...
          ├── HScrollbar（水平滚动条）
          └── VScrollbar（垂直滚动条）

技术亮点：
  - Canvas 滚动容器：支持内容超出视口时自动出现滚动条
  - 事件冒泡：卡片事件通过回调链向上传递到 MainWindow 控制器
  - 局部刷新：move_card_to_column() 仅在 UI 层面移动卡片，无需全量重建
"""

# =============================================================================
# 导入区
# =============================================================================

import tkinter as tk  # Python 标准 GUI 库，提供 Canvas、Frame、Scrollbar 等基础组件

# ---- 模型层 ----
from models.project import Project  # 项目实体类：包含名称、编号、截止日期、阶段归属等字段
from models.workflow import WorkflowStage  # 流程阶段实体类：包含 ID、名称、排序序号、显示颜色、列宽

# ---- 视图层 ----
from ui.kanban_column import KanbanColumn  # 看板列组件：每个流程阶段对应一列，承载该阶段的项目卡片
from ui.project_card import ProjectCard  # 项目卡片组件：展示单个项目的摘要信息和操作按钮
from utils.config import Config  # 全局配置类：提供看板背景色、列宽等 UI 常量


class KanbanBoard(tk.Frame):
    """看板主容器组件 - 继承自 tk.Frame

    实现水平排列的列式看板布局，提供以下核心功能：
      - 双向滚动：Canvas 画布 + 水平/垂直双滚动条，支持列多或卡片多时的流畅浏览
      - 列管理：load_stages() 根据阶段数据动态创建/重建所有列
      - 卡片单选：全局维护 selected_card 引用，同一时间最多一张卡片被选中
      - 阶段移动：响应卡片左/右箭头按钮，计算前后相邻列并通知控制器
      - 列宽调整：响应列拖拽手柄事件，通知控制器保存新宽度

    Attributes:
        columns (list[KanbanColumn]): 所有看板列组件列表（按阶段顺序排列）
        selected_card (ProjectCard | None): 当前选中的卡片（全局唯一，None 表示无选中）
        on_card_click: 卡片单击回调（选中/取消选中）
        on_card_double_click: 卡片双击回调（打开编辑对话框）
        on_card_detail: 详情按钮回调（打开详情窗口）
        on_card_edit: 编辑按钮回调（打开编辑对话框）
        on_card_copy: 复制按钮回调（复制项目创建副本）
        on_card_move_stage: 卡片箭头移动回调（将项目移动到目标阶段）
        on_column_resize: 列宽拖拽完成回调（保存新宽度）
    """

    def __init__(self, parent, **kwargs):
        """初始化看板容器

        Args:
            parent: 父级容器（通常为 MainWindow 主窗口实例）
            **kwargs: 传递给父类 tk.Frame 的额外关键字参数（如颜色、尺寸限制等）
        """
        # 调用父类 tk.Frame 构造方法，设置看板统一背景色
        super().__init__(parent, bg=Config.KANBAN_BG, **kwargs)

        # ---- 公共属性 ----
        self.columns: list[KanbanColumn] = []  # 列组件列表，按阶段顺序存储
        self.selected_card: ProjectCard | None = None  # 当前选中的卡片引用（None 表示无选中）

        # ---- 回调函数指针（由 MainWindow 在创建看板后绑定） ----
        self.on_card_click = None  # 卡片单击 -> 选中/取消选中
        self.on_card_double_click = None  # 卡片双击 -> 打开编辑对话框
        self.on_card_detail = None  # "详情"按钮 -> 打开项目详情窗口
        self.on_card_edit = None  # "编辑"按钮 -> 打开项目编辑对话框
        self.on_card_copy = None  # "复制"按钮 -> 复制当前项目
        self.on_card_move_stage = None  # 箭头按钮 -> 移动项目到前/后阶段
        self.on_column_resize = None  # 列宽拖拽完成 -> 保存新宽度

        # ---- 构建 UI 结构 ----
        self._build_ui()  # 创建 Canvas 画布、滚动条、列容器等组件

    # ==================================================================================
    # UI 构建
    # ==================================================================================

    def _build_ui(self):
        """构建看板的 UI 结构

        布局设计（由内到外）：
          1. columns_container（列容器 Frame）-- 所有看板列的直接父容器
          2. Canvas（滚动画布）-- 容纳 columns_container，提供滚动视口
          3. HScrollbar（水平滚动条）-- 控制看板左右平移
          4. VScrollbar（垂直滚动条）-- 控制看板上下滚动

        滚动机制：
          - Canvas 通过 create_window() 将 columns_container 放置在画布内部
          - columns_container 的 Configure 事件触发时，自动更新 Canvas 的 scrollregion
          - 滚动条通过 xscrollcommand/yscrollcommand 与 Canvas 双向联动
        """
        # --- 创建 Canvas 画布（所有内容的滚动容器） ---
        self._canvas = tk.Canvas(
            self, bg=Config.KANBAN_BG,  # 背景色与看板一致
            highlightthickness=0,  # 无高亮边框，保持界面简洁
        )

        # --- 创建水平滚动条 ---
        self._h_scrollbar = tk.Scrollbar(
            self, orient=tk.HORIZONTAL,  # 水平方向
            command=self._canvas.xview,  # 绑定到 Canvas 的 X 轴视图控制
        )

        # --- 创建垂直滚动条 ---
        self._v_scrollbar = tk.Scrollbar(
            self, orient=tk.VERTICAL,  # 垂直方向
            command=self._canvas.yview,  # 绑定到 Canvas 的 Y 轴视图控制
        )

        # --- 创建列容器 Frame（所有看板列放置在此 Frame 内） ---
        self._columns_container = tk.Frame(self._canvas, bg=Config.KANBAN_BG)

        # 监听列容器大小变化，自动更新 Canvas 的滚动区域范围
        # bbox("all") 返回所有画布内容的边界矩形，用于确定滚动区域大小
        self._columns_container.bind("<Configure>",
                                     lambda e: self._canvas.configure(
                                         scrollregion=self._canvas.bbox("all")))

        # 在 Canvas 中创建窗口对象（将列容器 Frame 嵌入画布）
        # anchor="nw" 表示窗口左上角锚定在 Canvas 的 (0,0) 坐标
        # tags="columns_win" 添加标签，便于后续通过 itemconfig 操作该窗口
        self._canvas.create_window(
            (0, 0), window=self._columns_container, anchor="nw",
            tags="columns_win",
        )

        # 配置 Canvas 与滚动条的双向通信
        self._canvas.configure(
            xscrollcommand=self._h_scrollbar.set,  # Canvas 更新 -> 通知水平滚动条
            yscrollcommand=self._v_scrollbar.set,  # Canvas 更新 -> 通知垂直滚动条
        )

        # --- 布局：滚动条固定边，Canvas 填充剩余空间 ---
        self._v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  # 垂直滚动条在右侧，垂直填充
        self._h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)  # 水平滚动条在底部，水平填充
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Canvas 填充剩余空间

        # --- 事件绑定 ---
        self._canvas.bind("<Configure>", self._on_canvas_resize)  # 画布大小变化 -> 调整列容器高度
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)  # 普通滚轮 -> 垂直滚动
        self._canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)  # Shift+滚轮 -> 水平滚动

    # ==================================================================================
    # Canvas 大小与滚动事件处理
    # ==================================================================================

    def _on_canvas_resize(self, event):
        """处理 Canvas 画布大小变化事件

        当主窗口大小变化时，Tkinter 自动调整 Canvas 的尺寸。
        此方法同步更新 Canvas 内部列容器窗口的高度，使其与可视区域一致。
        这样列内部带有滚动条的 CardArea 才能正确限高并启用滚动。

        Args:
            event: Tkinter 的 Configure 事件对象，event.height 为新的画布高度
        """
        if event.height > 80:  # 最小高度保护：避免窗口极小化时出现负高度
            # 通过标签 "columns_win" 定位 Canvas 内部的列容器窗口，更新其高度
            self._canvas.itemconfig("columns_win", height=event.height)

    def _on_mousewheel(self, event):
        """处理鼠标滚轮垂直滚动事件

        当用户在看板区域滚动鼠标滚轮时触发（上下翻页）。

        Args:
            event: Tkinter 的 MouseWheel 事件对象，event.delta 为滚轮增量（正=向上滚，负=向下滚）
        """
        # event.delta / 120：标准化滚轮增量（Windows 下一次滚轮增量为 ±120）
        # 取负号：向上滚（delta>0）应使视图内容向下移动（yview_scroll 负方向）
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event):
        """处理 Shift+鼠标滚轮横向滚动事件

        按住 Shift 键的同时滚动鼠标滚轮，实现看板的左右平移。
        适用于列数较多、需要横向浏览的场景。

        Args:
            event: Tkinter 的 MouseWheel 事件对象
        """
        self._canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    # ==================================================================================
    # 列管理 - 创建、销毁、维护看板中的所有列
    # ==================================================================================

    def load_stages(self, stages: list[WorkflowStage], projects: list[Project]):
        """根据阶段列表和项目列表重建整个看板

        这是看板内容的完整重建入口，执行以下步骤：
          1. 销毁所有现有的列组件（释放 Tkinter 资源和内存）
          2. 清空列列表
          3. 根据阶段列表创建新列（每个阶段创建一列）
          4. 将项目按 stage_id 分发到对应的列中
          5. 为每张卡片设置统一的交互回调函数

        通常在以下场景调用：
          - 应用启动时的初始化加载
          - 流程阶段配置变更后（刷新看板）
          - 项目增删改后（全量刷新）

        Args:
            stages: 流程阶段列表，按 order 字段升序排列
            projects: 所有项目列表，不限排序
        """
        # 第一步：销毁所有现有列组件
        for col in self.columns:
            col.destroy()  # 销毁 Tkinter 组件，释放 UI 资源
        self.columns.clear()  # 清空列列表引用

        # 第二步：根据阶段列表创建新列
        for stage in stages:
            col = KanbanColumn(self._columns_container, stage)  # 创建列组件，传入阶段数据
            col.on_card_click = self._handle_card_click  # 设置列的卡片单击回调
            col.on_card_double_click = self._handle_card_double_click  # 设置列的卡片双击回调
            col.on_column_click = self._handle_column_click  # 设置列的空白区域点击回调
            col.on_resize = self._handle_column_resize  # 设置列的宽度拖拽完成回调
            col.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)  # 左排列，垂直填充，5px 外边距
            self.columns.append(col)  # 加入列列表

        # 第三步：按公司名称分组项目，同公司同阶段合并为一张卡片
        from collections import defaultdict
        groups = defaultdict(list)
        for p in projects:
            key = (p.company_name.strip() or "未命名", p.stage_id)
            groups[key].append(p)
        for (company, sid), proj_list in groups.items():
            self._add_project_to_column(proj_list)

    def _add_project_to_column(self, project):
        """将项目(组)添加到其阶段对应的列中。

        Args:
            project: 单个 Project 或 list[Project]（同公司同阶段的合并组）
        """
        proj_list = project if isinstance(project, list) else [project]
        sid = proj_list[0].stage_id
        last_sid = self.columns[-1].stage.id if self.columns else None
        for col in self.columns:
            if col.stage.id == sid:
                card = col.add_card(proj_list[0], last_stage_id=last_sid)
                card.projects = proj_list
                self._setup_card_callbacks(card)
                return
        if self.columns:
            card = self.columns[0].add_card(project, last_stage_id=last_sid)
            self._setup_card_callbacks(card)

    def _setup_card_callbacks(self, card: ProjectCard):
        """为卡片组件统一绑定所有交互回调函数

        每张卡片创建后必须调用此方法，将看板层的回调转发给卡片。
        这样当用户操作卡片（点击箭头、详情按钮等）时，事件通过回调链最终到达 MainWindow。

        Args:
            card: 需要设置回调的 ProjectCard 实例
        """
        card.on_move_prev = self._handle_move_prev  # 左箭头 -> 移至前一阶段
        card.on_move_next = self._handle_move_next  # 右箭头 -> 移至后一阶段
        card.on_detail = self._handle_card_detail  # "详情"按钮 -> 打开详情窗口
        card.on_edit = self._handle_card_edit  # "编辑"按钮 -> 打开编辑对话框
        card.on_copy = self._handle_card_copy  # "复制"按钮 -> 复制项目

    # ==================================================================================
    # 阶段移动处理 - 响应卡片箭头按钮，计算目标阶段并通知控制器
    # ==================================================================================

    def _handle_move_prev(self, card: ProjectCard):
        """处理卡片左箭头（◀）点击 - 将项目移至上一阶段

        计算逻辑：
          1. 找到卡片当前所在列的索引
          2. 如果当前不是第一列（索引 > 0），获取前一列对应的阶段 ID
          3. 触发外部回调（MainWindow._on_card_move_stage），由控制器执行实际移动

        Args:
            card: 被点击左箭头的项目卡片组件
        """
        current_idx = self._get_stage_index_for_card(card)  # 获取卡片当前所在列的索引位置
        if current_idx > 0:  # 不是第一列，存在上一阶段
            target_stage_id = self.columns[current_idx - 1].stage.id  # 获取前一列对应的阶段 ID
            if self.on_card_move_stage:  # 回调已设置（防御性检查）
                self.on_card_move_stage(card, target_stage_id)  # 通知控制器执行移动

    def _handle_move_next(self, card: ProjectCard):
        """处理卡片右箭头（▶）点击 - 将项目移至下一阶段

        计算逻辑：
          1. 找到卡片当前所在列的索引
          2. 如果当前不是最后一列（索引 < len-1），获取后一列对应的阶段 ID
          3. 触发外部回调（MainWindow._on_card_move_stage），由控制器执行实际移动

        Args:
            card: 被点击右箭头的项目卡片组件
        """
        current_idx = self._get_stage_index_for_card(card)  # 获取卡片当前所在列的索引位置
        if current_idx < len(self.columns) - 1:  # 不是最后一列，存在下一阶段
            target_stage_id = self.columns[current_idx + 1].stage.id  # 获取后一列对应的阶段 ID
            if self.on_card_move_stage:  # 回调已设置（防御性检查）
                self.on_card_move_stage(card, target_stage_id)  # 通知控制器执行移动

    def _get_stage_index_for_card(self, card: ProjectCard) -> int:
        """获取卡片所在列的索引（在 columns 列表中的位置）

        遍历所有列，检查每列的 cards 列表中是否包含指定卡片。

        Args:
            card: 要查找的项目卡片组件

        Returns:
            int: 列索引（从 0 开始），如果未找到则返回 -1
        """
        for i, col in enumerate(self.columns):  # enumerate 同时获取索引和列对象
            if card in col.cards:  # 检查卡片是否在该列的卡片列表中
                return i  # 找到，返回索引
        return -1  # 未找到（仅在异常情况下发生）

    # ==================================================================================
    # 卡片交互事件处理 - 选中/取消选中、双击、详情、编辑、复制
    # ==================================================================================

    def _handle_card_click(self, card: ProjectCard):
        """处理卡片单击事件 - 实现全局单选逻辑

        行为规则：
          - 点击已选中的卡片：取消选中（toggle off -> 无选中状态）
          - 点击其他卡片：先取消所有卡的选中状态，再选中被点击的卡片

        Args:
            card: 被单击的项目卡片组件
        """
        if self.selected_card is card:  # 点击的是已经选中的卡片
            # 取消选中：清除所有卡片选中状态，清空引用
            self._deselect_all()
            self.selected_card = None  # 置空，表示当前无选中
        else:  # 点击的是一张未被选中的卡片
            # 先取消之前可能存在的选中卡片，然后选中当前卡片
            self._deselect_all()
            card.set_selected(True)  # 设置当前卡片为选中状态（蓝色加粗边框）
            self.selected_card = card  # 更新全局选中引用

        if self.on_card_click:  # 回调已设置（防御性检查）
            self.on_card_click(self.selected_card)  # 通知控制器选中状态变化

    def _handle_card_double_click(self, card: ProjectCard):
        """处理卡片双击事件 - 直接打开项目编辑对话框

        这是一种快捷操作入口，跳过详情窗口直接进入编辑模式。

        Args:
            card: 被双击的项目卡片组件
        """
        if self.on_card_double_click:  # 回调已设置
            self.on_card_double_click(card)

    def _handle_card_detail(self, card: ProjectCard):
        """处理"详情"按钮点击事件 - 打开项目详情窗口

        详情窗口展示项目的完整信息（所有字段、操作日志、阶段变更历史等）。

        Args:
            card: 被点击"详情"按钮的项目卡片组件
        """
        if self.on_card_detail:  # 回调已设置
            self.on_card_detail(card)

    def _handle_card_edit(self, card: ProjectCard):
        """处理"编辑"按钮点击事件 - 打开项目编辑对话框

        与双击行为相同，直接进入编辑模式。

        Args:
            card: 被点击"编辑"按钮的项目卡片组件
        """
        if self.on_card_edit:  # 回调已设置
            self.on_card_edit(card)

    def _handle_card_copy(self, card: ProjectCard):
        """处理"复制"按钮点击事件 - 复制当前项目创建副本

        副本的各项属性与源项目一致，公司名称后追加" - 副本"后缀。

        Args:
            card: 被点击"复制"按钮的项目卡片组件
        """
        if self.on_card_copy:  # 回调已设置
            self.on_card_copy(card)

    def _handle_column_click(self, column: KanbanColumn):
        """处理列空白区域点击事件 - 取消所有卡片的选中状态

        当用户点击列中没有卡片的空白区域时触发，用于快速清除选中状态。

        Args:
            column: 被点击的列组件（用于调用其 deselect_all 方法）
        """
        column.deselect_all()  # 取消该列所有卡片的选中状态
        self.selected_card = None  # 清除全局选中引用
        if self.on_card_click:  # 回调已设置
            self.on_card_click(None)  # 通知控制器：当前无选中（None）

    def _handle_column_resize(self, column: KanbanColumn, new_width: int):
        """处理列宽拖拽完成事件 - 通知控制器保存新的列宽

        当用户拖拽列右侧的分隔手柄释放后触发。

        Args:
            column: 被调整宽度的列组件
            new_width: 调整后的列宽度（单位：像素）
        """
        if self.on_column_resize:  # 回调已设置
            self.on_column_resize(column.stage.id, new_width)  # 传递阶段 ID 和新宽度

    def _deselect_all(self):
        """取消所有列中所有卡片的选中状态

        遍历每个列，调用列的 deselect_all() 方法批量清除选中状态。
        通常在选中新卡片之前或清除选中时调用。
        """
        for col in self.columns:  # 遍历所有列
            col.deselect_all()  # 每列自己负责清除其下的所有卡片选中

    # ==================================================================================
    # 公开方法 - 供 MainWindow 控制器调用的接口
    # ==================================================================================

    def refresh(self, stages: list[WorkflowStage], projects: list[Project]):
        """刷新整个看板内容，并尝试恢复之前选中的卡片状态

        与 load_stages() 的区别：
          load_stages() 仅重建列和卡片，不处理选中状态
          refresh() 在重建后尝试恢复用户在刷新前选中的卡片

        通常在数据变更后调用（如编辑项目、删除项目等全量刷新场景）。

        Args:
            stages: 最新的流程阶段列表
            projects: 最新的项目列表
        """
        selected_id = self.selected_card.project.id if self.selected_card else None  # 保存刷新前选中项目 ID
        self.load_stages(stages, projects)  # 重建所有列和卡片

        # 尝试恢复之前的选中状态
        if selected_id:  # 刷新前有选中的项目
            for col in self.columns:  # 遍历所有列
                card = col.find_card_by_project_id(selected_id)  # 按项目 ID 查找卡片
                if card:  # 找到目标卡片
                    card.set_selected(True)  # 恢复选中状态（蓝色边框）
                    self.selected_card = card  # 更新全局选中引用
                    break  # 找到即退出

    def move_card_to_column(self, card: ProjectCard, target_stage_id: str):
        """将卡片从当前列移动到目标阶段列（局部 UI 更新，无需全量刷新）

        执行步骤：
          1. 从源列中移除卡片（destroy 旧组件，从 cards 列表删除）
          2. 更新项目对象的 stage_id 为目标阶段
          3. 在目标列中创建新卡片（置顶插入 position="top"）
          4. 为新卡片重新绑定所有交互回调

        这种局部更新方式比全量刷新更高效：
          - 无需销毁所有列重建
          - 保留其他卡片的 UI 状态
          - 移动后的卡片自动置于目标列顶部

        Args:
            card: 要移动的项目卡片组件（移动后将被销毁，新卡片替换）
            target_stage_id: 目标阶段的唯一标识符
        """
        for col in self.columns:  # 遍历所有列
            if col.stage.id == target_stage_id:  # 找到目标列
                for src_col in self.columns:
                    if card in src_col.cards:
                        src_col.remove_card(card)
                        break
                # 更新所有项目数据中的阶段 ID
                for p in (card.projects or [card.project]):
                    p.stage_id = target_stage_id
                last_sid = self.columns[-1].stage.id if self.columns else None
                new_card = col.add_card(card.projects[0] if card.projects else card.project,
                                        position="top", last_stage_id=last_sid)
                new_card.projects = card.projects
                self._setup_card_callbacks(new_card)
                return

    def get_selected_project_id(self) -> str | None:
        """获取当前选中卡片的项目 ID

        Returns:
            str | None: 选中项目的唯一标识符（UUID 字符串），无选中时返回 None
        """
        if self.selected_card:  # 有卡片被选中
            return self.selected_card.project.id  # 返回该卡片关联的项目 ID
        return None  # 无选中卡片
