"""
看板列组件 - 表示流程中的一个阶段列

每个列包含：
- 列标题（阶段名称 + 项目计数）
- 可滚动的卡片列表区域
- 点击列空白区域可取消选中卡片
"""

import tkinter as tk  # 导入Tkinter GUI库，用于构建桌面应用界面组件
from models.project import Project  # 导入Project模型类，表示一个等保测评项目实体
from models.workflow import WorkflowStage  # 导入WorkflowStage模型类，表示一个流程阶段实体
from ui.project_card import ProjectCard  # 导入ProjectCard卡片组件，用于在列中显示项目
from utils.config import Config  # 导入Config配置类，获取颜色、尺寸等UI配置常量


class KanbanColumn(tk.Frame):
    """看板列组件 - 继承自tk.Frame

    一个列对应流程中的一个阶段（如"需求分析"、"渗透测试"等），
    包含项目卡片列表。支持接收拖拽放下的项目。

    Attributes:
        stage: 关联的流程阶段实体（WorkflowStage实例）
        cards: 列中的卡片列表（ProjectCard列表）
        on_card_click: 卡片点击回调函数
        on_card_double_click: 卡片双击回调函数
        on_drop: 拖拽放下回调函数（预留）
        on_column_click: 列背景点击回调函数
    """

    def __init__(self, parent, stage: WorkflowStage, **kwargs):
        """初始化看板列

        Args:
            parent: 父级容器（看板的列容器Frame）
            stage: 流程阶段实体，包含阶段名称、颜色、ID等信息
            **kwargs: 传递给父类tk.Frame的额外关键字参数
        """
        # 调用父类初始化，设置列背景色和边框
        super().__init__(parent, bg=Config.COLUMN_BG,
                         highlightbackground="#c0c4cc",
                         highlightthickness=1, **kwargs)

        self.stage = stage  # 保存关联的流程阶段实体
        self.cards: list[ProjectCard] = []  # 初始化列内的卡片列表（类型标注）
        self.on_card_click = None  # 卡片单击回调
        self.on_card_double_click = None  # 卡片双击回调
        self.on_column_click = None  # 列空白区域点击回调
        self.on_resize = None  # 拖拽调整列宽完成后的回调 (col, new_width)

        # 计算列宽：阶段自定义值或系统默认值
        self._col_w = self.stage.column_width or Config.COLUMN_WIDTH
        self._resize_start_x = 0  # 拖拽起始X坐标
        self._resize_start_w = 0  # 拖拽起始列宽
        self._resizing = False  # 是否正在拖拽调整宽度

        self._build_header()  # 构建列标题栏
        self._build_cards_area()  # 构建卡片可滚动区域
        self._build_resize_grip()  # 构建拖拽调整宽度手柄

        # 固定列宽（含滚动条宽度，防止 pack fill 拉伸覆盖自定义宽度）
        self.configure(width=self._col_w + 22)

    def _build_header(self):
        """构建列标题栏

        标题栏使用阶段对应的颜色作为背景，显示阶段名称（左侧）
        和当前列的项目计数（右侧）。
        """
        header = tk.Frame(self, bg=self.stage.color, height=36)  # 标题栏，阶段颜色背景，高36像素
        header.pack(fill=tk.X, padx=0, pady=0)  # 水平填充
        header.pack_propagate(False)  # 禁止子组件撑开，保持36像素固定高度

        # 阶段名称标签 - 左侧，白色粗体文字
        self._title_label = tk.Label(
            header, text=self.stage.name,
            bg=self.stage.color, fg="white",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
        )
        self._title_label.pack(side=tk.LEFT, padx=10)  # 左侧放置，水平10px内边距

        # 项目计数标签 - 右侧，白色文字，初始显示"0"
        self._count_label = tk.Label(
            header, text="0",
            bg=self.stage.color, fg="white",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
        )
        self._count_label.pack(side=tk.RIGHT, padx=10)  # 右侧放置

    def _build_cards_area(self):
        """构建卡片滚动区域

        使用Canvas + Frame + Scrollbar组合实现可垂直滚动的卡片区域。
        Canvas作为滚动容器，Frame容纳所有卡片，Scrollbar控制滚动。
        """
        # 创建Canvas画布作为滚动容器
        self._canvas = tk.Canvas(
            self, bg=Config.COLUMN_BG,
            highlightthickness=0, width=self._col_w,
            height=Config.CARD_MIN_HEIGHT + 20,
        )
        # 创建垂直滚动条
        self._scrollbar = tk.Scrollbar(
            self, orient=tk.VERTICAL, command=self._canvas.yview,  # 垂直方向，绑定Canvas的yview
        )
        # 创建卡片容器Frame，放置在Canvas内部
        self._cards_frame = tk.Frame(self._canvas, bg=Config.COLUMN_BG)

        # 当卡片容器大小变化时，自动更新Canvas的滚动区域
        self._cards_frame.bind("<Configure>",
                               lambda e: self._canvas.configure(
                                   scrollregion=self._canvas.bbox("all")))  # bbox("all")获取所有内容的边界矩形

        # 在Canvas中创建窗口对象，放置卡片容器Frame
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._cards_frame, anchor="nw",  # 锚定左上角
            width=self._col_w - 20,  # 宽度减20像素（为滚动条留空间）
        )

        # 配置Canvas接收滚动条的scroll命令
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  # 滚动条放右侧，垂直填充
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Canvas填充剩余空间

        # 列宽度自适应 - 当列Frame大小变化时调整内部Canvas窗口宽度
        self.bind("<Configure>", self._on_column_resize)

        # 列内鼠标滚轮翻页 - 绑定到Canvas和卡片容器
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._cards_frame.bind("<MouseWheel>", self._on_mousewheel)

        # 点击空白区域的事件 - 用于取消卡片选中
        self._canvas.bind("<Button-1>", self._on_bg_click)
        self._cards_frame.bind("<Button-1>", self._on_bg_click)

    def _build_resize_grip(self):
        """构建右侧列宽拖拽手柄 —— 4px 宽的拖拽条，用于鼠标拖拽调整列宽"""
        self._grip = tk.Frame(self, bg="#c0c4cc", width=4, cursor="sb_h_double_arrow")
        self._grip.pack(side=tk.RIGHT, fill=tk.Y, padx=0, pady=0)

        # 绑定拖拽事件
        self._grip.bind("<Button-1>", self._on_grip_press)
        self._grip.bind("<B1-Motion>", self._on_grip_drag)
        self._grip.bind("<ButtonRelease-1>", self._on_grip_release)

    def _on_grip_press(self, event):
        """拖拽手柄按下：记录起始位置和宽度"""
        self._resizing = True
        self._resize_start_x = event.x_root  # 屏幕坐标X
        self._resize_start_w = self._col_w  # 当前列宽
        self._grip.configure(bg="#3498db")  # 高亮手柄

    def _on_grip_drag(self, event):
        """拖拽手柄移动：实时调整列宽"""
        if not self._resizing:
            return
        dx = event.x_root - self._resize_start_x  # 鼠标移动量
        new_w = max(120, self._resize_start_w + dx)  # 最小列宽120px
        self._apply_width(new_w)

    def _on_grip_release(self, event):
        """拖拽手柄释放：保存新宽度"""
        if not self._resizing:
            return
        self._resizing = False
        self._grip.configure(bg="#c0c4cc")  # 恢复手柄颜色
        # 同步到 stage 数据
        self.stage.column_width = self._col_w
        # 通知外部保存
        if self.on_resize:
            self.on_resize(self, self._col_w)

    def _apply_width(self, new_w):
        """应用列宽 —— 更新所有相关组件宽度"""
        self._col_w = new_w
        self.configure(width=new_w + 22)
        self._canvas.configure(width=new_w)
        self._canvas.itemconfig(self._canvas_window, width=new_w - 20)

    def _on_column_resize(self, event):
        """列宽度变化时调整卡片区域宽度

        当看板列被拖动调整宽度时，同步更新Canvas内部窗口的宽度，
        确保卡片内容正确适应新宽度。

        Args:
            event: Tkinter的Configure事件对象，包含新的宽度信息
        """
        new_width = event.width - 22  # 减去滚动条和边距的宽度
        if new_width > 50:  # 最小宽度保护，避免太窄
            self._canvas.itemconfig(self._canvas_window, width=new_width)  # 更新Canvas窗口宽度

    def _on_mousewheel(self, event):
        """列内鼠标滚轮上下翻页

        仅在内容超出可见区域（需要滚动）时才响应滚轮事件，
        避免内容未溢出时产生无响应的情况。

        Args:
            event: Tkinter的MouseWheel事件对象
        """
        if self._cards_frame.winfo_height() <= self._canvas.winfo_height():
            return  # 内容未溢出，不需要滚动，直接返回
        # delta/120 标准化滚轮增量，负号调整方向（向上滚动delta为正，需要内容向上/scroll向下）
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_bg_click(self, event):
        """点击列空白区域取消选中

        当用户点击列中没有卡片的空白区域时，取消所有卡片的选中状态。

        Args:
            event: Tkinter的Button-1事件对象
        """
        if self.on_column_click:
            self.on_column_click(self)

    def add_card(self, project: Project, position: str = "bottom") -> ProjectCard:
        """添加项目卡片到列中

        根据项目实体创建新的ProjectCard组件，添加到列的卡片列表中，
        并按position参数决定插入位置（顶部或底部）。

        Args:
            project: 项目实体对象
            position: 插入位置，"top" 表示插入到列表顶部，"bottom" 表示追加到列表底部

        Returns:
            ProjectCard: 创建的卡片组件实例
        """
        card = ProjectCard(self._cards_frame, project)  # 创建卡片组件
        card.on_click = self.on_card_click  # 传递卡片单击回调
        card.on_double_click = self.on_card_double_click  # 传递卡片双击回调

        # 先打包到底部，插入列表正确位置
        card.pack(fill=tk.X, padx=4, pady=2, ipady=2)  # 水平填充，边距和内边距
        if position == "top":
            self.cards.insert(0, card)  # 插入到列表索引0位置（最顶部）
        else:
            self.cards.append(card)  # 追加到列表末尾

        # 按列表顺序重排所有卡片的视觉位置，确保 top 真正置顶
        for i, c in enumerate(self.cards):
            if i == 0:
                # 第一张卡片：放在所有其他卡片之前
                c.pack_configure(before=self.cards[1] if len(self.cards) > 1 else None)
            else:
                # 后续卡片：放在前一张卡片之后
                c.pack_configure(after=self.cards[i - 1])

        self._update_count()  # 更新列标题中的项目计数
        return card

    def remove_card(self, card: ProjectCard):
        """从列中移除卡片

        从cards列表中移除指定卡片，销毁其UI组件，并更新计数。

        Args:
            card: 要移除的ProjectCard卡片组件
        """
        if card in self.cards:
            self.cards.remove(card)  # 从列表中移除
            card.destroy()  # 销毁Tkinter组件释放资源
            self._update_count()  # 更新项目计数

    def clear_cards(self):
        """清空列中的所有卡片

        遍历销毁所有卡片组件并清空列表，通常在刷新看板时调用。
        """
        for card in self.cards[:]:  # 使用切片副本遍历，避免修改正在迭代的列表
            card.destroy()  # 销毁卡片组件
        self.cards.clear()  # 清空卡片列表
        self._update_count()  # 更新计数为0

    def _update_count(self):
        """更新列标题中的项目计数显示

        将当前cards列表的长度显示在标题栏右侧的计数标签中。
        """
        self._count_label.configure(text=str(len(self.cards)))

    def select_card(self, card: ProjectCard):
        """选中指定卡片，取消其他卡片的选中状态

        实现单选逻辑：同一列中同时只能有一张卡片处于选中状态。

        Args:
            card: 要选中的ProjectCard卡片组件
        """
        for c in self.cards:
            c.set_selected(c is card)  # 仅目标卡片设为True，其他设为False

    def deselect_all(self):
        """取消列中所有卡片的选中状态

        遍历所有卡片将其选中状态设为False。
        """
        for c in self.cards:
            c.set_selected(False)

    def find_card_by_project_id(self, project_id: str) -> ProjectCard | None:
        """根据项目ID查找列中的卡片

        在cards列表中搜索匹配project_id的卡片，用于刷新时恢复选中状态。

        Args:
            project_id: 项目的唯一标识符（UUID字符串）

        Returns:
            ProjectCard | None: 找到的卡片组件，未找到返回None
        """
        for c in self.cards:
            if c.project.id == project_id:  # 比较卡片关联项目的ID
                return c
        return None
