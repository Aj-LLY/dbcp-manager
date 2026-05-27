"""
看板组件 - 整个看板视图的容器

管理所有列组件，处理：
- 列的创建、排列和滚动
- 卡片选中状态管理
- 卡片箭头按钮的阶段移动
"""

import tkinter as tk  # 导入Tkinter GUI库，用于构建桌面应用界面组件
from models.project import Project  # 导入Project模型类，表示一个等保测评项目实体
from models.workflow import WorkflowStage  # 导入WorkflowStage模型类，表示一个流程阶段实体
from ui.kanban_column import KanbanColumn  # 导入KanbanColumn看板列组件
from ui.project_card import ProjectCard  # 导入ProjectCard卡片组件
from utils.config import Config  # 导入Config配置类，获取颜色等UI配置常量


class KanbanBoard(tk.Frame):
    """看板主组件 - 继承自tk.Frame

    水平排列的列式看板，支持：
    - 横向滚动查看所有流程阶段
    - 卡片箭头按钮阶段移动（左/右箭头）
    - 统一的卡片选中管理（全局单选）

    Attributes:
        columns: 所有列组件列表（KanbanColumn列表）
        selected_card: 当前选中的卡片（ProjectCard或None）
        on_card_click: 卡片单击回调函数
        on_card_double_click: 卡片双击回调函数
        on_card_detail: 详情按钮回调函数
        on_card_edit: 编辑按钮回调函数
        on_card_move_stage: 卡片箭头按钮移动回调函数
    """

    def __init__(self, parent, **kwargs):
        """初始化看板

        Args:
            parent: 父级容器（主窗口对象）
            **kwargs: 传递给父类tk.Frame的额外关键字参数
        """
        # 调用父类初始化，使用看板背景色
        super().__init__(parent, bg=Config.KANBAN_BG, **kwargs)

        self.columns: list[KanbanColumn] = []  # 初始化列组件列表（类型标注）
        self.selected_card: ProjectCard | None = None  # 当前选中的卡片（初始无选中）
        self.on_card_click = None  # 卡片单击回调
        self.on_card_double_click = None  # 卡片双击回调
        self.on_card_detail = None  # 详情按钮回调 - 打开项目详情窗口
        self.on_card_edit = None  # 编辑按钮回调 - 打开编辑对话框
        self.on_card_move_stage = None  # 卡片箭头按钮移动阶段回调

        self._build_ui()  # 构建看板的UI结构

    def _build_ui(self):
        """构建看板UI结构

        使用Canvas + Scrollbar实现可双向滚动的看板视图：
        - 水平滚动条：在列数较多时横向滚动查看
        - 垂直滚动条：在卡片较多时纵向滚动查看
        - 列容器Frame放置在Canvas内部
        """
        # 创建主Canvas画布作为滚动容器
        self._canvas = tk.Canvas(
            self, bg=Config.KANBAN_BG, highlightthickness=0,  # 无高亮边框
        )
        # 创建水平滚动条 - 控制Canvas的X轴滚动
        self._h_scrollbar = tk.Scrollbar(
            self, orient=tk.HORIZONTAL, command=self._canvas.xview,
        )
        # 创建垂直滚动条 - 控制Canvas的Y轴滚动
        self._v_scrollbar = tk.Scrollbar(
            self, orient=tk.VERTICAL, command=self._canvas.yview,
        )

        # 创建列容器Frame - 所有看板列都放置在此Frame内
        self._columns_container = tk.Frame(self._canvas, bg=Config.KANBAN_BG)

        # 当列容器大小变化时，自动更新Canvas的滚动区域
        self._columns_container.bind("<Configure>",
                                     lambda e: self._canvas.configure(
                                         scrollregion=self._canvas.bbox("all")))  # bbox("all")获取所有内容的边界

        # 在Canvas中创建窗口对象，放置列容器Frame，标记为 "columns_win" 便于后续引用
        self._canvas.create_window(
            (0, 0), window=self._columns_container, anchor="nw",  # 锚定左上角
            tags="columns_win",  # 添加标签用于后续itemconfig操作
        )

        # 配置Canvas的双向滚动命令
        self._canvas.configure(
            xscrollcommand=self._h_scrollbar.set,  # 水平滚动条联动
            yscrollcommand=self._v_scrollbar.set,  # 垂直滚动条联动
        )

        # 布局滚动条和Canvas
        self._v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  # 垂直滚动条：右侧，垂直填充
        self._h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)  # 水平滚动条：底部，水平填充
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Canvas：填充剩余空间

        # 画布大小变化时，约束列容器高度 = 视口高度（使列内滚动条生效）
        self._canvas.bind("<Configure>", self._on_canvas_resize)

        # 鼠标滚轮支持
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)  # 普通滚轮：垂直滚动
        self._canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)  # Shift+滚轮：水平滚动

    def _on_canvas_resize(self, event):
        """画布大小变化时，将列容器高度约束为画布可视高度

        当主窗口大小变化时，同步调整Canvas内部列容器窗口的高度，
        确保列容器高度与Canvas可视区域保持一致，让列内滚动条正常工作。

        Args:
            event: Tkinter的Configure事件对象
        """
        if event.height > 80:  # 最小高度保护
            self._canvas.itemconfig("columns_win", height=event.height)  # 通过标签名更新窗口高度

    def _on_mousewheel(self, event):
        """鼠标滚轮垂直滚动

        Args:
            event: Tkinter的MouseWheel事件对象
        """
        # delta/120 标准化滚轮增量，负号调整方向
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event):
        """Shift+鼠标滚轮横向滚动

        按住Shift键的同时滚动鼠标滚轮，实现看板的左右平移。

        Args:
            event: Tkinter的MouseWheel事件对象
        """
        self._canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    # ==================== 列管理 ====================

    def load_stages(self, stages: list[WorkflowStage], projects: list[Project]):
        """根据阶段列表和项目列表重建看板

        销毁所有现有列，根据阶段列表创建新列，然后将项目分配到对应列中。
        通常在刷新看板或初始化时调用。

        Args:
            stages: 流程阶段列表（按order排序）
            projects: 所有项目列表
        """
        # 销毁所有现有的列组件
        for col in self.columns:
            col.destroy()
        self.columns.clear()  # 清空列列表

        # 根据阶段列表创建新列
        for stage in stages:
            col = KanbanColumn(self._columns_container, stage)  # 创建列组件
            col.on_card_click = self._handle_card_click  # 设置卡片单击回调
            col.on_card_double_click = self._handle_card_double_click  # 设置卡片双击回调
            col.on_column_click = self._handle_column_click  # 设置列空白点击回调
            col.pack(side=tk.LEFT, fill=tk.BOTH, padx=3, pady=3)  # 左排列，双向填充，间距3px
            self.columns.append(col)  # 加入列列表

        # 将项目分配到对应的列中
        for project in projects:
            self._add_project_to_column(project)

    def _add_project_to_column(self, project: Project):
        """将项目添加到对应的列中，并设置所有交互回调

        根据项目的stage_id匹配列，找到对应列后添加卡片。
        如果找不到匹配列（阶段被删除等情况），默认添加到第一列。

        Args:
            project: 要添加的项目实体
        """
        for col in self.columns:
            if col.stage.id == project.stage_id:  # 找到匹配的阶段列
                card = col.add_card(project)  # 在匹配列中添加卡片
                self._setup_card_callbacks(card)  # 设置卡片的所有交互回调
                return
        # 如果找不到匹配阶段，添加到第一列作为兜底处理
        if self.columns:
            card = self.columns[0].add_card(project)
            self._setup_card_callbacks(card)

    def _setup_card_callbacks(self, card: ProjectCard):
        """为卡片设置所有交互回调

        统一设置卡片的移动箭头、详情和编辑按钮的回调函数。

        Args:
            card: 需要设置回调的ProjectCard卡片组件
        """
        card.on_move_prev = self._handle_move_prev  # 左箭头：移至上一阶段
        card.on_move_next = self._handle_move_next  # 右箭头：移至下一阶段
        card.on_detail = self._handle_card_detail  # 详情按钮
        card.on_edit = self._handle_card_edit  # 编辑按钮

    def _handle_move_prev(self, card: ProjectCard):
        """卡片左箭头点击：将项目移至上一阶段

        找到卡片当前所在列的索引，如果有前一列，则触发移动回调。

        Args:
            card: 被点击的ProjectCard卡片组件
        """
        current_idx = self._get_stage_index_for_card(card)  # 获取卡片当前所在列索引
        if current_idx > 0:  # 不是第一列，可以前移
            target_stage_id = self.columns[current_idx - 1].stage.id  # 获取前一列阶段ID
            if self.on_card_move_stage:
                self.on_card_move_stage(card, target_stage_id)  # 触发外部移动回调

    def _handle_move_next(self, card: ProjectCard):
        """卡片右箭头点击：将项目移至下一阶段

        找到卡片当前所在列的索引，如果有后一列，则触发移动回调。

        Args:
            card: 被点击的ProjectCard卡片组件
        """
        current_idx = self._get_stage_index_for_card(card)  # 获取卡片当前所在列索引
        if current_idx < len(self.columns) - 1:  # 不是最后一列，可以后移
            target_stage_id = self.columns[current_idx + 1].stage.id  # 获取后一列阶段ID
            if self.on_card_move_stage:
                self.on_card_move_stage(card, target_stage_id)  # 触发外部移动回调

    def _get_stage_index_for_card(self, card: ProjectCard) -> int:
        """获取卡片所在列的索引

        遍历所有列，查找包含指定卡片的列的索引位置。

        Args:
            card: 要查找的ProjectCard卡片组件

        Returns:
            int: 列索引（从0开始），未找到返回-1
        """
        for i, col in enumerate(self.columns):
            if card in col.cards:  # 检查卡片是否在该列的卡片列表中
                return i
        return -1  # 未找到

    # ==================== 卡片交互处理 ====================

    def _handle_card_click(self, card: ProjectCard):
        """处理卡片点击：选中/取消选中

        实现卡片单选逻辑：
        - 点击已选中的卡片：取消选中
        - 点击未选中的卡片：选中，取消之前的选中

        Args:
            card: 被点击的ProjectCard卡片组件
        """
        if self.selected_card is card:
            # 点击已选中的卡片：取消选中
            self._deselect_all()
            self.selected_card = None
        else:
            # 点击其他卡片：先取消所有选中，再选中当前卡片
            self._deselect_all()
            card.set_selected(True)
            self.selected_card = card

        if self.on_card_click:
            self.on_card_click(self.selected_card)  # 通知外部状态变化

    def _handle_card_double_click(self, card: ProjectCard):
        """处理卡片双击 -- 直接打开编辑对话框

        Args:
            card: 被双击的ProjectCard卡片组件
        """
        if self.on_card_double_click:
            self.on_card_double_click(card)

    def _handle_card_detail(self, card: ProjectCard):
        """详情按钮 -- 打开项目详情窗口

        Args:
            card: 被点击详情的ProjectCard卡片组件
        """
        if self.on_card_detail:
            self.on_card_detail(card)

    def _handle_card_edit(self, card: ProjectCard):
        """编辑按钮 -- 直接打开编辑对话框

        Args:
            card: 被点击编辑的ProjectCard卡片组件
        """
        if self.on_card_edit:
            self.on_card_edit(card)

    def _handle_column_click(self, column: KanbanColumn):
        """点击列空白区域取消所有选中

        当用户点击列中没有卡片的空白区域时触发。

        Args:
            column: 被点击的KanbanColumn列组件
        """
        column.deselect_all()  # 取消该列所有卡片选中
        self.selected_card = None  # 清除选中状态引用
        if self.on_card_click:
            self.on_card_click(None)  # 通知外部选中状态已清除

    def _deselect_all(self):
        """取消所有卡片（所有列）的选中状态"""
        for col in self.columns:
            col.deselect_all()

    # ==================== 公开方法 ====================

    def refresh(self, stages: list[WorkflowStage], projects: list[Project]):
        """刷新整个看板内容

        重建看板列和卡片，并尝试恢复之前选中的卡片状态。
        通常在数据变更后调用。

        Args:
            stages: 最新的流程阶段列表
            projects: 最新的项目列表
        """
        selected_id = self.selected_card.project.id if self.selected_card else None  # 保存当前选中项目ID
        self.load_stages(stages, projects)  # 重建所有列和卡片

        # 尝试恢复之前的选中状态
        if selected_id:
            for col in self.columns:
                card = col.find_card_by_project_id(selected_id)  # 按项目ID查找卡片
                if card:
                    card.set_selected(True)  # 恢复选中
                    self.selected_card = card  # 更新选中引用
                    break

    def move_card_to_column(self, card: ProjectCard,
                            target_stage_id: str):
        """将卡片移动到指定阶段列（自动刷新无需手动操作）

        从源列中移除卡片，在目标列中重新创建卡片（置顶），
        并自动更新项目的阶段ID和卡片的所有回调。

        Args:
            card: 要移动的ProjectCard卡片组件
            target_stage_id: 目标阶段的唯一标识符
        """
        for col in self.columns:
            if col.stage.id == target_stage_id:  # 找到目标列
                # 从当前列中移除卡片
                for src_col in self.columns:
                    if card in src_col.cards:
                        src_col.remove_card(card)  # 从源列移除
                        break
                # 更新项目阶段并创建新卡片（置顶，带完整回调）
                card.project.stage_id = target_stage_id  # 更新项目数据的阶段ID
                new_card = col.add_card(card.project, position="top")  # 在目标列顶部添加新卡片
                self._setup_card_callbacks(new_card)  # 设置新卡片的所有交互回调
                return

    def get_selected_project_id(self) -> str | None:
        """获取当前选中卡片的项目ID

        Returns:
            str | None: 选中项目的ID，无选中时返回None
        """
        if self.selected_card:
            return self.selected_card.project.id
        return None
