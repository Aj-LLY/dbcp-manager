"""
主窗口模块 - 应用程序的主界面控制器

本模块是整个"等保测评进度管理系统"的核心控制器（Controller），遵循 MVC 设计模式：
  - Model（模型层）：models 包中的 Project、WorkflowStage 等实体类
  - View（视图层）：ui 包中的 Toolbar、KanbanBoard、ProjectCard 等组件
  - Controller（控制层）：MainWindow 自身，负责协调视图与模型的交互

主要职责：
  1. 工具栏、看板等 UI 组件的创建和布局管理
  2. 业务服务层（数据、项目、流程、日志）的初始化与依赖注入
  3. 用户交互事件（按钮点击、卡片操作、窗口事件）的响应与分发
  4. 窗口生命周期管理（创建时加载数据、关闭时自动保存）

技术栈：
  - Tkinter：Python 标准 GUI 库，提供窗口、Frame、组件等
  - 服务层注入：DataService / ProjectService / WorkflowService / LogService
"""

# =============================================================================
# 导入区 - 按层级组织
# =============================================================================

import tkinter as tk  # Python 标准 GUI 库，用于构建桌面端窗口和容器组件
from tkinter import messagebox  # 消息弹窗组件，用于显示提示、警告、错误和信息确认对话框

# ---- 模型层 ----
from models.workflow import WorkflowStage  # 流程阶段实体类，表示看板中的一列（如"项目启动"）

# ---- 服务层 ----
from services.data_service import DataService  # 数据持久化服务：负责 JSON 文件的读写操作
from services.project_service import ProjectService  # 项目业务服务：处理项目的增删改查和阶段移动
from services.workflow_service import WorkflowService  # 流程业务服务：管理流程阶段的配置和宽度
from services.log_service import LogService  # 日志服务：记录和查询所有操作日志

# ---- 视图层 ----
from ui.toolbar import Toolbar  # 顶部工具栏组件，包含新增、编辑、删除等快捷按钮
from ui.kanban_board import KanbanBoard  # 看板容器组件，承载所有流程阶段列和项目卡片
from ui.flow_canvas import FlowCanvas  # 流程图画布，以节点拓扑图方式展示项目流程
from ui.project_card import ProjectCard  # 项目卡片组件（仅用于类型标注和回调参数类型提示）
from ui.project_dialog import show_project_dialog  # 项目编辑对话框便捷函数（新增/编辑项目表单）
from ui.workflow_dialog import WorkflowDialog  # 流程编辑对话框类，管理流程阶段的增删改排序
from ui.log_dialog import show_log_dialog  # 日志查看对话框便捷函数（展示操作历史记录）
from ui.detail_dialog import show_detail_dialog  # 项目详情对话框便捷函数（展示项目完整信息）
from ui.backup_dialog import BackupDialog  # WebDAV 备份对话框类，负责远程备份管理

# ---- 工具层 ----
from utils.config import Config  # 全局配置类，提供应用名称、版本、窗口尺寸、颜色等常量

# ---- 控制层 ----
from controllers.project_handlers import (
    on_add_project, on_delete_selected, on_card_selected,
    on_card_detail, on_card_edit, on_card_copy,
    on_card_move_stage, on_column_resize,
    pick_project_from_card, create_project_folder,
    generate_nda_template,
)
from controllers.startup_handlers import (
    on_console, on_backup, on_close,
    check_restore_on_startup,
)


class MainWindow(tk.Tk):
    """应用程序主窗口 - 继承自 tk.Tk（Tkinter 顶层窗口）

    作为整个应用的控制器，MainWindow 负责串联所有子系统：
      - 创建并注入服务层依赖（DataService、ProjectService、WorkflowService、LogService）
      - 构建并布局 UI 组件（Toolbar 工具栏 + KanbanBoard 看板）
      - 绑定用户交互事件的回调函数（按钮点击、卡片操作、窗口调整）
      - 管理窗口生命周期（初始化加载数据、关闭前保存数据）

    设计原则：
      - 单一数据源：所有业务数据通过服务层管理，UI 仅负责展示
      - 事件驱动：UI 组件通过回调函数通知控制器处理业务逻辑
      - 依赖注入：服务层实例在 __init__ 中创建并传递给需要的组件

    Attributes:
        _data_service (DataService): 数据持久化服务实例
        _log_service (LogService): 操作日志服务实例
        _project_service (ProjectService): 项目业务服务实例
        _workflow_service (WorkflowService): 流程业务服务实例
        _toolbar (Toolbar): 顶部工具栏组件
        _kanban (KanbanBoard): 主看板组件
    """

    def __init__(self):
        """初始化主窗口及所有子系统

        初始化顺序严格按照依赖关系执行：
          1. 创建服务层实例（DataService -> LogService -> ProjectService -> WorkflowService）
          2. 配置窗口属性（标题、尺寸、最小尺寸、背景色）
          3. 构建 UI 组件（先工具栏、后看板）
          4. 绑定窗口事件（大小变化监听、关闭协议钩子）
          5. 加载数据并刷新看板显示
        """
        super().__init__()  # 调用父类 tk.Tk 的构造方法，创建顶级窗口

        # =====================================================================
        # 第一步：初始化服务层（数据 -> 日志 -> 项目 -> 流程，按依赖顺序创建）
        # =====================================================================

        # --- 数据服务：处理 JSON 文件的读写，是所有数据持久化的入口 ---
        data_file = Config.get_data_file_path()  # 获取主数据文件完整路径（如 ./data/dap_data.json）
        self._data_service = DataService(data_file)  # 创建数据服务实例并传入文件路径

        # --- 日志服务：记录和查询所有用户操作日志（增删改、阶段移动等） ---
        self._log_service = LogService()  # 创建日志服务实例（内部自行管理日志文件路径）

        # --- 项目服务：封装所有项目相关的业务逻辑 ---
        self._project_service = ProjectService(
            self._data_service,  # 注入数据服务：项目操作需要读写 JSON 文件
            log_callback=self._log_service.create_log_callback(),  # 注入日志回调：每个项目操作自动记录日志
        )

        # --- 流程服务：管理流程阶段（列）的配置，包括阶段颜色、宽度、顺序等 ---
        self._workflow_service = WorkflowService(
            self._data_service,  # 注入数据服务：流程阶段数据同样保存在 JSON 文件中
            log_callback=self._log_service.create_log_callback(),  # 注入日志回调：流程编辑操作自动记录
        )

        # =====================================================================
        # 第二步：配置窗口基本属性
        # =====================================================================

        self.title(f"{Config.APP_NAME} v{Config.APP_VERSION}")
        # 恢复上次窗口位置和大小，首次使用默认值
        try:
            import json, os
            geo_path = os.path.join(Config.get_data_dir(), "data", "window_geometry.json")
            if os.path.exists(geo_path):
                with open(geo_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.geometry(saved.get("geometry", f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}"))
            else:
                self.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
        except Exception:
            self.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
        self.minsize(Config.WINDOW_MIN_WIDTH, Config.WINDOW_MIN_HEIGHT)
        self.configure(bg=Config.KANBAN_BG)

        # =====================================================================
        # 第三步：构建 UI 组件（从上到下：工具栏 -> 看板）
        # =====================================================================

        self._build_toolbar()
        self._build_kanban()
        self._build_flow_view()  # 流程图视图（初始隐藏）
        self._current_view = "kanban"  # 当前视图模式

        # =====================================================================
        # 第四步：绑定窗口级别的全局事件
        # =====================================================================

        self.bind("<Configure>", self._on_window_resize)  # 窗口大小变化时触发（预留扩展点）
        self.protocol("WM_DELETE_WINDOW", self._on_close)  # 点击关闭按钮时，先保存数据再退出

        # =====================================================================
        # 第五步：加载数据并刷新看板（从服务层读取阶段和项目数据，渲染到 UI）
        # =====================================================================

        self._refresh_kanban()
        # 启动后延迟检测云端备份（等 UI 完全加载）
        self.after(1000, self._check_restore_on_startup)

    # ==================================================================================
    # UI 构建方法 - 创建和布局所有界面组件
    # ==================================================================================

    def _build_toolbar(self):
        """构建顶部工具栏组件

        创建 Toolbar 实例并固定在窗口顶部（pack 布局，top 侧对齐，水平填充）。
        设置工具栏各个按钮的回调函数，将按钮点击事件连接到对应的业务处理方法。

        工具栏按钮对应关系：
          - "新增项目"  -> _on_add_project()    # 打开新增项目对话框
          - "编辑流程"  -> _on_edit_workflow()   # 打开流程阶段配置对话框
          - "查看日志"  -> _on_view_logs()       # 打开操作日志查看窗口
          - "删除项目"  -> _on_delete_selected() # 删除当前选中的项目
          - "刷新"      -> _refresh_kanban()     # 重新加载数据并刷新看板
          - "WebDAV备份" -> _on_backup()         # 打开 WebDAV 备份管理对话框
        """
        self._toolbar = Toolbar(self)  # 创建工具栏组件实例，父容器为当前主窗口（self）
        self._toolbar.pack(fill=tk.X, side=tk.TOP)  # 固定在顶部，水平方向填充整个窗口宽度

        # 绑定工具栏各按钮的回调函数 - 将 UI 事件连接到 MainWindow 的业务处理方法
        self._toolbar.on_add_project = self._on_add_project  # "新增项目" 按钮 -> 新增项目处理
        self._toolbar.on_edit_workflow = self._on_edit_workflow  # "编辑流程" 按钮 -> 流程编辑处理
        self._toolbar.on_view_logs = self._on_view_logs  # "操作日志" 按钮 -> 查看日志处理
        self._toolbar.on_delete_project = self._on_delete_selected  # "删除项目" 按钮 -> 删除选中项目
        self._toolbar.on_refresh = self._refresh_kanban  # "刷新" 按钮 -> 刷新看板数据
        self._toolbar.on_backup = self._on_backup
        self._toolbar.on_console = self._on_console

        # 视图切换按钮
        self._view_btn = tk.Button(
            self._toolbar, text="流程图", command=self._toggle_view,
            bg="#8e44ad", fg="white", cursor="hand2", relief="flat",
            font=("Microsoft YaHei", 9), padx=10,
            activebackground="#7d3c98",
        )
        self._view_btn.pack(side=tk.RIGHT, padx=5)

    def _toggle_view(self):
        """在看板和流程图之间切换。"""
        if self._current_view == "kanban":
            self._kanban.pack_forget()
            self._flow_container.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
            self._current_view = "flow"
            self._view_btn.configure(text="看板")
            self._refresh_flow_view()
        else:
            self._flow_container.pack_forget()
            self._kanban.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
            self._current_view = "kanban"
            self._view_btn.configure(text="流程图")

    def _build_flow_view(self):
        """构建流程图视图 + 右侧信息面板。"""
        self._flow_container = tk.Frame(self, bg="#f5f6fa")
        self._flow_canvas = FlowCanvas(self._flow_container)
        self._flow_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._flow_canvas.bind_callbacks(
            on_subnode_click=self._on_flow_subnode_click,
            on_subnode_double=self._on_flow_subnode_double,
        )
        # 右侧信息面板
        self._info_panel = tk.Frame(self._flow_container, bg="white", width=260,
                                     highlightbackground="#d0d5dd", highlightthickness=1)
        self._info_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self._info_panel.pack_propagate(False)
        self._build_info_panel()

    def _build_info_panel(self):
        """构建右侧信息面板的静态框架。"""
        panel = self._info_panel
        tk.Label(panel, text="项目详情", bg="white", fg="#2c3e50",
                 font=("Microsoft YaHei", 12, "bold")).pack(pady=(15, 10))
        tk.Frame(panel, bg="#d0d5dd", height=1).pack(fill=tk.X, padx=12)
        self._info_content = tk.Frame(panel, bg="white")
        self._info_content.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        self._info_labels = {}
        for label in ["公司名称", "系统名称", "证书编号", "下证日期",
                       "系统等级", "属地", "交付日期", "当前阶段", "备注"]:
            row = tk.Frame(self._info_content, bg="white")
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label + "：", bg="white", fg="#7f8c8d",
                     font=("Microsoft YaHei", 9), width=8, anchor="e").pack(side=tk.LEFT)
            val = tk.Label(row, text="-", bg="white", fg="#2c3e50",
                          font=("Microsoft YaHei", 9), anchor="w", justify="left")
            val.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._info_labels[label] = val
        # 底部提示
        tk.Label(panel, text="双击打开详情 | 右键节点连线条",
                 bg="#f0f2f5", fg="#95a5a6",
                 font=("Microsoft YaHei", 8)).pack(side=tk.BOTTOM, fill=tk.X, pady=5)

    def _on_flow_subnode_click(self, project_id):
        print(f'[Main] _on_flow_subnode_click: project_id={project_id}')
        """单击子节点 → 右侧面板显示详情。"""
        project = self._project_service.get_project_by_id(project_id)
        print(f'[Main] 查询项目: found={project is not None}', flush=True)
        if not project:
            print(f'[Main] ⚠ 项目未找到: {project_id}', flush=True)
            return
        print(f'[Main] 项目数据: company={project.company_name} sys={project.system_name}', flush=True)
        stages = self._workflow_service.get_all_stages()
        stage_name = "未知"
        for s in stages:
            if s.id == project.stage_id:
                stage_name = s.name
                break
        data = {
            "公司名称": project.company_name or "-",
            "系统名称": project.system_name or "-",
            "证书编号": project.cert_number or "-",
            "下证日期": project.issue_date or "-",
            "系统等级": project.level or "-",
            "属地": project.location or "-",
            "交付日期": project.deadline or "-",
            "当前阶段": stage_name,
            "备注": project.notes or "-",
        }
        for label, val in self._info_labels.items():
            val.configure(text=data.get(label, "-"))
        self._info_panel.update()  # 强制刷新面板

    def _refresh_flow_view(self):
        print(f'[Main] _refresh_flow_view called')
        """刷新流程图数据。"""
        stages = self._workflow_service.get_all_stages()
        projects = self._project_service.get_all_projects()
        print(f"[主窗口] _refresh_flow_view: stages={[s.name for s in stages]} projects={len(projects)}", flush=True)
        self._flow_canvas.load(stages, projects)

    def _on_flow_subnode_click(self, project_id):
        print(f'[Main] _on_flow_subnode_click: project_id={project_id}')
        """流程图子节点单击 → 选中高亮。"""
        pass  # 预留：可添加选中高亮逻辑

    def _on_flow_subnode_double(self, project_id):
        print(f'[Main] _on_flow_subnode_double: project_id={project_id}')
        """流程图子节点双击 → 打开详情。"""
        project = self._project_service.get_project_by_id(project_id)
        if project:
            from controllers.project_handlers import on_card_detail
            class _TempCard:
                project = project
                projects = [project]
            on_card_detail(self, _TempCard())

    def _build_kanban(self):
        """构建看板区域组件

        创建 KanbanBoard 实例并放置在工具栏下方（fill=BOTH + expand=True 使其填充所有剩余空间）。
        设置看板内各种用户交互事件的回调函数，将卡片操作连接到控制器的业务处理方法。

        看板交互事件对应关系：
          - 卡片单击      -> _on_card_selected()    # 选中/取消选中卡片
          - 卡片双击      -> _on_card_edit()        # 打开编辑对话框
          - 详情按钮      -> _on_card_detail()      # 打开项目详情窗口
          - 编辑按钮      -> _on_card_edit()        # 打开编辑对话框（同双击）
          - 箭头移动      -> _on_card_move_stage()  # 将项目移动到前/后阶段
          - 复制按钮      -> _on_card_copy()        # 复制当前项目
          - 列宽拖拽      -> _on_column_resize()    # 保存调整后的列宽
        """
        self._kanban = KanbanBoard(self)  # 创建看板组件实例，父容器为当前主窗口
        self._kanban.pack(fill=tk.BOTH, expand=True, side=tk.TOP)  # 填充剩余空间，可随窗口缩放

        # 绑定看板中各种卡片操作的回调函数
        self._kanban.on_card_click = self._on_card_selected  # 卡片单点 -> 选中/取消选中
        self._kanban.on_card_double_click = self._on_card_edit  # 卡片双击 -> 打开项目编辑对话框
        self._kanban.on_card_detail = self._on_card_detail  # "详情" 按钮 -> 打开项目详情窗口
        self._kanban.on_card_edit = self._on_card_edit  # "编辑" 按钮 -> 打开项目编辑对话框
        self._kanban.on_card_move_stage = self._on_card_move_stage  # 箭头按钮 -> 移动项目阶段
        self._kanban.on_card_copy = self._on_card_copy  # "复制" 按钮 -> 复制当前项目
        self._kanban.on_column_resize = self._on_column_resize  # 列宽拖拽 -> 保存新宽度

    # ==================================================================================
    # 工具栏事件处理方法 - 响应顶部工具栏各按钮的点击
    # ==================================================================================

    def _on_add_project(self):
        """处理"新增项目"按钮点击事件

        委托给 controllers.project_handlers.on_add_project 处理。
        该函数打开 ProjectDialog 收集用户输入，创建新的 Project 对象，
        保存到数据服务并刷新看板。
        """
        on_add_project(self)

    def _on_edit_workflow(self):
        """处理"编辑流程"按钮点击事件

        打开 WorkflowDialog 流程编辑器，允许用户进行以下操作：
          - 新增流程阶段（填写名称、选择颜色）
          - 删除现有阶段（移除不需要的步骤）
          - 重命名阶段名称
          - 调整阶段之间的排列顺序（上移/下移）

        保存后的容错处理：
          - 如果某个阶段被删除，则该阶段下的所有项目自动迁移到新配置的第一个阶段
          - 避免出现"孤儿项目"（项目归属于不存在的阶段）

        操作完成后记录日志并刷新看板。
        """
        old_stages = self._workflow_service.get_all_stages()  # 获取修改前的阶段列表（用于对比哪些阶段被删除）
        dialog = WorkflowDialog(self, old_stages)  # 打开流程编辑对话框，传入当前阶段列表
        self.wait_window(dialog)  # 等待对话框关闭（模态阻塞，用户操作期间主窗口不可交互）

        if dialog.result:  # 用户点击了"保存"按钮，dialog.result 为编辑后的阶段配置列表
            # 将新的流程配置保存到数据服务（直接替换所有阶段数据）
            self._data_service.replace_all_stages(dialog.result)

            # 检测被删除的阶段：计算新旧阶段 ID 集合的差集
            new_stage_ids = {s["id"] for s in dialog.result}  # 新配置中的所有阶段 ID（转为集合）
            old_stage_ids = {s.id for s in old_stages}  # 旧配置中的所有阶段 ID（转为集合）
            removed_ids = old_stage_ids - new_stage_ids  # 差集 = 被删除的阶段 ID

            if removed_ids and new_stage_ids:  # 确实有阶段被删除，且新配置中至少还保留一个阶段
                first_new_id = dialog.result[0]["id"]  # 获取新配置的第一个阶段 ID（作为兜底目标）
                for pid in removed_ids:  # 遍历每一个被删除的阶段 ID
                    # 查找所有归属于被删除阶段的项目
                    for proj in self._project_service.get_all_projects():
                        if proj.stage_id == pid:  # 发现一个"孤儿项目"
                            # 将该项目的阶段更新为新配置的第一个阶段
                            self._project_service.update_project(
                                proj.id,  # 项目唯一 ID
                                stage_id=first_new_id,  # 迁移到第一个阶段
                            )

            # 记录本次编辑流程的操作日志
            self._log_service.add_log(
                action="编辑流程",  # 操作类型
                detail="更新流程阶段配置",  # 操作详细描述
            )
            self._refresh_kanban()  # 刷新看板显示（反映阶段配置的最新变化）

    def _on_view_logs(self):
        """处理"查看日志"按钮点击事件

        从日志服务获取所有系统操作记录，然后打开日志查看对话框展示给用户。
        日志按时间倒序排列，最新记录显示在最前面。
        """
        logs = self._log_service.get_all_logs()  # 获取所有操作日志列表（已按时间倒序排列）
        show_log_dialog(self, logs)  # 打开日志查看对话框，展示日志内容

    def _on_console(self):
        """处理"控制台"按钮点击事件

        委托给 controllers.startup_handlers.on_console 处理。
        打开系统控制台窗口（用于调试和开发者操作）。
        """
        on_console(self)

    def _on_backup(self):
        """处理"WebDAV 备份"按钮点击事件

        委托给 controllers.startup_handlers.on_backup 处理。
        打开 BackupDialog 备份管理对话框，支持 WebDAV 服务器配置、
        备份上传、恢复下载和文件管理。
        """
        on_backup(self)

    def _on_delete_selected(self):
        """处理"删除项目"按钮点击事件

        委托给 controllers.project_handlers.on_delete_selected 处理。
        获取当前选中的项目卡片，弹出二次确认对话框，确认后永久删除项目
        并从数据服务和看板中移除。
        """
        on_delete_selected(self)

    # ==================================================================================
    # 看板事件处理方法 - 响应看板中卡片的交互操作
    # ==================================================================================

    def _on_card_selected(self, card: ProjectCard | None):
        """处理卡片选中/取消选中事件

        委托给 controllers.project_handlers.on_card_selected 处理。
        当看板中某张卡片被单击选中或取消选中时触发，更新工具栏按钮状态
        （如"删除项目"按钮仅在选中时可用）。

        Args:
            card: 被选中的卡片组件，None 表示取消所有选中
        """
        on_card_selected(self, card)

    def _pick_project_from_card(self, card: ProjectCard) -> Project | None:
        """从卡片组件中提取关联的 Project 实体对象

        委托给 controllers.project_handlers.pick_project_from_card 处理。
        根据卡片的 project 属性查找数据服务中的对应项目。

        Args:
            card: 项目卡片组件

        Returns:
            Project | None: 找到的项目实体，未找到返回 None
        """
        return pick_project_from_card(self, card)

    def _on_card_detail(self, card: ProjectCard):
        """处理"详情"按钮点击事件 - 打开项目详情窗口

        委托给 controllers.project_handlers.on_card_detail 处理。
        获取卡片的关联项目数据和操作日志，打开 DetailDialog 详情窗口。

        Args:
            card: 被点击"详情"按钮的项目卡片组件
        """
        on_card_detail(self, card)

    def _on_card_edit(self, card: ProjectCard):
        """处理"编辑"按钮点击事件 - 打开项目编辑对话框

        委托给 controllers.project_handlers.on_card_edit 处理。
        获取卡片的关联项目数据，打开 ProjectDialog 编辑对话框，
        保存后刷新看板显示。

        Args:
            card: 被点击"编辑"按钮的项目卡片组件
        """
        on_card_edit(self, card)

    def _on_card_move_stage(self, card: ProjectCard, target_stage_id: str):
        """处理卡片箭头移动事件 - 将项目移至目标流程阶段

        委托给 controllers.project_handlers.on_card_move_stage 处理。
        更新项目的 stage_id，调用看板的局部移动方法更新 UI，
        保存操作日志并更新排序顺序。

        Args:
            card: 被移动的项目卡片组件
            target_stage_id: 目标阶段的唯一标识符（UUID 字符串）
        """
        on_card_move_stage(self, card, target_stage_id)

    def _on_card_copy(self, card: ProjectCard):
        """处理"复制"按钮点击事件 - 创建项目的副本

        委托给 controllers.project_handlers.on_card_copy 处理。
        复制当前项目的所有属性（公司名称后缀追加" - 副本"），
        保存新项目到数据服务并刷新看板。

        Args:
            card: 被点击"复制"按钮的项目卡片组件
        """
        on_card_copy(self, card)

    def _on_column_resize(self, stage_id: str, new_width: int):
        """处理列宽拖拽完成事件 - 保存调整后的列宽

        委托给 controllers.project_handlers.on_column_resize 处理。
        将新的列宽值通过 WorkflowService 保存到数据文件，
        确保下次启动时恢复用户的列宽偏好。

        Args:
            stage_id: 被调整宽度的阶段唯一标识符
            new_width: 调整后的列宽度（像素值）
        """
        on_column_resize(self, stage_id, new_width)

    def _create_project_folder(self, project):
        """为项目创建本地文件夹结构

        委托给 controllers.project_handlers.create_project_folder 处理。
        在项目根目录下创建子目录结构（如测评方案、测评报告等）。

        Args:
            project: 项目实体对象，用于获取路径和名称信息
        """
        create_project_folder(self, project)

    def _generate_nda_template(self, root, cname_clean, company_name):
        """生成保密承诺书（NDA）模板文件

        委托给 controllers.project_handlers.generate_nda_template 处理。
        在指定目录下创建 .docx 格式的保密承诺书模板文件。

        Args:
            root: 目标目录路径
            cname_clean: 清理后的公司名称（去掉特殊字符）
            company_name: 原始公司名称
        """
        generate_nda_template(self, root, cname_clean, company_name)

    # ==================================================================================
    # 窗口事件处理方法
    # ==================================================================================

    def _on_window_resize(self, event):
        """处理窗口大小变化事件（预留扩展）

        Tkinter 的 pack 布局管理器会自动处理组件的大小调整，
        此方法作为预留扩展点，可在此添加额外的自适应逻辑，
        例如：当窗口宽度低于阈值时折叠工具栏。

        Args:
            event: Tkinter 的 Configure 事件对象（包含新窗口尺寸等信息）
        """
        pass  # 当前无需额外处理，pack 布局自动完成自适应

    def _on_close(self):
        """处理窗口关闭事件 - 在退出前保存数据

        委托给 controllers.startup_handlers.on_close 处理。
        在用户点击窗口关闭按钮或按 Alt+F4 时触发，执行以下操作：
          1. 保存当前窗口的几何信息（位置和尺寸）到 window_geometry.json
          2. 确保数据文件已保存
          3. 销毁所有子窗口，退出应用程序
        """
        on_close(self)

    def _check_restore_on_startup(self):
        """应用启动后延迟检测云端备份（延时 1000ms 后执行）

        委托给 controllers.startup_handlers.check_restore_on_startup 处理。
        在 UI 完全加载后，检查 WebDAV 服务器上是否有比本地更新的备份文件，
        如果有则提示用户是否恢复。
        延迟 1 秒执行是为了确保主窗口已经完全渲染完毕。
        """
        check_restore_on_startup(self)

    # ==================================================================================
    # 内部辅助方法
    # ==================================================================================

    def _refresh_kanban(self):
        """刷新看板显示 - 从服务层重新加载所有数据并重建 UI

        这是数据变更后的统一 UI 刷新入口，所有导致看板内容变化的操作
        （新增、编辑、删除、移动项目，编辑流程等）最终都通过此方法刷新显示。

        执行流程：
          1. 从 WorkflowService 获取最新阶段列表
          2. 从 ProjectService 获取最新项目列表
          3. 调用 KanbanBoard.load_stages() 销毁旧组件、创建新列和卡片
        """
        stages = self._workflow_service.get_all_stages()  # 从流程服务获取最新阶段列表（含颜色、宽度）
        projects = self._project_service.get_all_projects()  # 从项目服务获取最新项目列表（含所有字段）
        self._kanban.load_stages(stages, projects)  # 看板重建所有列和卡片，完成渲染
