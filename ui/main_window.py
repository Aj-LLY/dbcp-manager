"""
主窗口 - 应用程序的主界面，负责协调所有UI组件和服务

作为整个应用的控制器（Controller），管理：
- 工具栏、看板等UI组件的创建和布局
- 业务服务层的初始化和调用
- 用户交互事件的响应和分发
- 窗口生命周期管理（关闭时自动保存数据）
"""

import tkinter as tk  # 导入Tkinter GUI库，作为主窗口的基类和UI组建基础
from tkinter import messagebox  # 导入messagebox，用于显示提示/警告/确认弹窗

from models.workflow import WorkflowStage  # 导入WorkflowStage模型类，用于流程阶段数据传递
from services.data_service import DataService  # 导入数据持久化服务（负责JSON文件读写）
from services.project_service import ProjectService  # 导入项目业务服务（负责项目增删改查）
from services.workflow_service import WorkflowService  # 导入流程业务服务（负责流程阶段管理）
from services.log_service import LogService  # 导入日志服务（负责操作日志记录和查询）
from ui.toolbar import Toolbar  # 导入工具栏组件
from ui.kanban_board import KanbanBoard  # 导入看板组件（主看板视图容器）
from ui.project_card import ProjectCard  # 导入卡片组件类型（用于回调类型标注）
from ui.project_dialog import show_project_dialog  # 导入项目编辑对话框便捷函数
from ui.workflow_dialog import WorkflowDialog  # 导入流程编辑对话框类
from ui.log_dialog import show_log_dialog  # 导入日志查看对话框便捷函数
from ui.detail_dialog import show_detail_dialog  # 导入项目详情对话框便捷函数
from ui.backup_dialog import BackupDialog  # 导入WebDAV备份对话框类
from utils.config import Config  # 导入Config配置类，获取应用名称、版本、窗口尺寸等配置


class MainWindow(tk.Tk):
    """应用程序主窗口 - 继承tk.Tk（Tkinter顶层窗口）

    继承tk.Tk，作为应用程序的顶层窗口。
    负责初始化所有服务层（数据、项目、流程、日志）、
    UI组件（工具栏、看板），并处理全局事件分发。

    设计遵循MVC模式：
    - Model: models包中的实体类
    - View: ui包中的各组件
    - Controller: MainWindow自身（协调View和Model的交互）
    """

    def __init__(self):
        """初始化主窗口和所有子系统

        初始化顺序：
        1. 创建服务层（数据、日志、项目、流程）
        2. 配置窗口属性（标题、大小、背景色）
        3. 构建UI组件（工具栏、看板）
        4. 绑定窗口事件（大小变化、关闭）
        5. 加载并显示数据
        """
        super().__init__()  # 调用父类tk.Tk的初始化方法

        # ---- 初始化服务层 ----
        # 数据服务：负责JSON文件的读写，所有数据持久化的入口
        data_file = Config.get_data_file_path()  # 获取数据文件的完整路径
        self._data_service = DataService(data_file)  # 创建数据服务实例

        # 日志服务：记录和查询所有操作日志（增删改等）
        self._log_service = LogService()

        # 项目服务：处理项目的增删改查业务逻辑
        self._project_service = ProjectService(
            self._data_service,  # 注入数据服务依赖
            log_callback=self._log_service.create_log_callback(),  # 注入日志回调，自动记录项目操作
        )

        # 流程服务：处理流程阶段的配置管理
        self._workflow_service = WorkflowService(
            self._data_service,  # 注入数据服务依赖
            log_callback=self._log_service.create_log_callback(),  # 注入日志回调
        )

        # ---- 窗口配置 ----
        self.title(f"{Config.APP_NAME} v{Config.APP_VERSION}")  # 设置窗口标题（应用名 + 版本号）
        self.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")  # 设置初始窗口大小
        self.minsize(Config.WINDOW_MIN_WIDTH, Config.WINDOW_MIN_HEIGHT)  # 设置最小窗口尺寸
        self.configure(bg=Config.KANBAN_BG)  # 设置窗口背景色（与看板背景一致）

        # ---- 构建UI ----
        self._build_toolbar()  # 构建顶部工具栏
        self._build_kanban()  # 构建主看板区域

        # ---- 绑定事件 ----
        self.bind("<Configure>", self._on_window_resize)  # 窗口大小变化时触发（预留扩展）
        self.protocol("WM_DELETE_WINDOW", self._on_close)  # 窗口关闭按钮触发保存数据

        # ---- 加载数据 ----
        self._refresh_kanban()  # 从服务层加载数据并刷新看板显示

    # ==================== UI构建 ====================

    def _build_toolbar(self):
        """构建顶部工具栏

        创建Toolbar实例并放置在窗口顶部，设置所有按钮的回调函数。
        工具栏采用pack布局，固定在顶部水平填充。
        """
        self._toolbar = Toolbar(self)  # 创建工具栏实例（父容器为self，即主窗口）
        self._toolbar.pack(fill=tk.X, side=tk.TOP)  # 固定在顶部，水平填充

        # 绑定工具栏各按钮的回调函数 - 每个按钮对应一个事件处理私有方法
        self._toolbar.on_add_project = self._on_add_project  # 新增项目
        self._toolbar.on_edit_workflow = self._on_edit_workflow  # 编辑流程
        self._toolbar.on_view_logs = self._on_view_logs  # 查看日志
        self._toolbar.on_delete_project = self._on_delete_selected  # 删除选中项目
        self._toolbar.on_refresh = self._refresh_kanban  # 刷新看板
        self._toolbar.on_backup = self._on_backup  # WebDAV备份

    def _build_kanban(self):
        """构建看板区域

        创建KanbanBoard实例并放置在工具栏下方，填充剩余空间。
        设置所有交互事件的回调函数。
        """
        self._kanban = KanbanBoard(self)  # 创建看板实例
        self._kanban.pack(fill=tk.BOTH, expand=True, side=tk.TOP)  # 填充剩余空间

        # 绑定看板交互事件的回调函数
        self._kanban.on_card_click = self._on_card_selected  # 卡片单击（选中/取消选中）
        self._kanban.on_card_double_click = self._on_card_edit  # 卡片双击（打开编辑）
        self._kanban.on_card_detail = self._on_card_detail  # 详情按钮（打开详情窗口）
        self._kanban.on_card_edit = self._on_card_edit  # 编辑按钮（打开编辑对话框）
        self._kanban.on_card_move_stage = self._on_card_move_stage  # 箭头按钮移动阶段
        self._kanban.on_card_copy = self._on_card_copy  # 复制按钮
        self._kanban.on_column_resize = self._on_column_resize  # 列宽拖拽

    # ==================== 工具栏事件处理 ====================

    def _on_add_project(self):
        """新增项目按钮的事件处理

        检查是否有可用的流程阶段，然后打开新增项目对话框。
        用户填写并确认后，通过ProjectService创建项目并刷新看板。
        """
        stages = self._workflow_service.get_all_stages()  # 获取所有流程阶段
        if not stages:
            messagebox.showwarning("提示", "请先配置流程阶段")  # 无阶段时提示用户
            return

        result = show_project_dialog(self, "新增项目", stages=stages)  # 打开新增对话框
        if result:  # 用户确认填写
            # 调用项目服务创建项目
            success, msg, project = self._project_service.create_project(
                company_name=result["company_name"],
                system_name=result["system_name"],
                cert_number=result["cert_number"],
                issue_date=result.get("issue_date", ""),
                level=result.get("level", ""),
                deadline=result["deadline"],
                notes=result["notes"],
                stage_id=result["stage_id"],
            )
            if success:
                self._create_project_folder(project)  # 创建项目文件夹
                self._refresh_kanban()
            else:
                messagebox.showerror("错误", msg)

    def _on_edit_workflow(self):
        """编辑流程按钮的事件处理

        打开WorkflowDialog让用户编辑流程阶段配置。
        保存后处理两种情况：
        - 阶段被删除：将相关项目移到第一个阶段
        - 阶段顺序变化：直接更新配置
        操作完成后记录日志并刷新看板。
        """
        old_stages = self._workflow_service.get_all_stages()  # 获取当前阶段列表（用于比较删除）
        dialog = WorkflowDialog(self, old_stages)  # 打开流程编辑对话框
        self.wait_window(dialog)  # 等待对话框关闭

        if dialog.result:  # 用户确认保存
            # 保存新流程配置到数据服务
            self._data_service.replace_all_stages(dialog.result)

            # 检查哪些阶段被删除了，将关联项目移到第一个阶段
            new_stage_ids = {s["id"] for s in dialog.result}  # 新配置的阶段ID集合
            old_stage_ids = {s.id for s in old_stages}  # 旧配置的阶段ID集合
            removed_ids = old_stage_ids - new_stage_ids  # 差集 = 被删除的阶段ID

            if removed_ids and new_stage_ids:  # 确实有阶段被删除且还有剩余阶段
                first_new_id = dialog.result[0]["id"]  # 新配置的第一个阶段ID
                for pid in removed_ids:  # 遍历所有被删除的阶段ID
                    # 找到属于被删除阶段的所有项目
                    for proj in self._project_service.get_all_projects():
                        if proj.stage_id == pid:
                            # 将项目移到第一个阶段
                            self._project_service.update_project(
                                proj.id, stage_id=first_new_id,
                            )

            # 记录操作日志
            self._log_service.add_log(
                action="编辑流程",
                detail="更新流程阶段配置",
            )
            self._refresh_kanban()  # 刷新看板

    def _on_view_logs(self):
        """查看日志按钮的事件处理

        获取所有系统操作日志，打开日志查看对话框。
        """
        logs = self._log_service.get_all_logs()  # 获取所有日志记录
        show_log_dialog(self, logs)  # 打开日志查看对话框

    def _on_backup(self):
        """WebDAV 备份按钮的事件处理

        打开WebDAV备份管理对话框，传入当前数据文件路径。
        """
        dialog = BackupDialog(self, Config.get_data_file_path())
        dialog.on_restore = lambda: (self._data_service.reload(), self._refresh_kanban())
        self.wait_window(dialog)

    def _on_delete_selected(self):
        """删除选中项目按钮的事件处理

        获取当前看板选中的项目ID，确认后删除。
        如果未选中任何卡片则提示用户先选择。
        """
        project_id = self._kanban.get_selected_project_id()  # 获取选中项目的ID
        if not project_id:
            messagebox.showinfo("提示", "请先在卡片上点击选择要删除的项目")  # 提示选择
            return

        project = self._project_service.get_project_by_id(project_id)  # 根据ID获取项目对象
        if not project:  # 防御性检查
            return

        # 二次确认删除
        if messagebox.askyesno("确认删除",
                               f"确定要永久删除项目\u300c{project.name}\u300d吗？\n\n"
                               "此操作不可撤销！"):
            success, msg = self._project_service.delete_project(project_id)  # 执行删除
            if success:
                self._refresh_kanban()  # 删除成功后刷新看板
            else:
                messagebox.showerror("错误", msg)

    # ==================== 看板事件处理 ====================

    def _on_card_selected(self, card: ProjectCard | None):
        """卡片选中状态变化时的处理

        预留的扩展点，可用于更新状态栏、启用/禁用操作按钮等。
        当前无具体逻辑。

        Args:
            card: 选中的卡片（None表示取消选中）
        """
        pass  # 可在此添加状态栏更新等逻辑，当前为空实现

    def _on_card_detail(self, card: ProjectCard):
        """详情按钮 / 查看项目详情的事件处理

        获取该项目的操作日志和所有阶段，打开详情对话框。
        根据用户操作分发处理：
        - edit: 编辑项目信息
        - delete: 删除项目
        - move: 项目阶段移动

        Args:
            card: 被点击详情的卡片组件
        """
        stages = self._workflow_service.get_all_stages()
        logs = self._log_service.get_project_logs(card.project.id)

        def _handle_move(target_stage_id, dialog):
            """移动项目并刷新对话框"""
            success, msg = self._project_service.move_project(
                card.project.id, target_stage_id)
            if success:
                self._refresh_kanban()
                upd = self._project_service.get_project_by_id(card.project.id)
                dialog.refresh_data(upd,
                    self._workflow_service.get_all_stages(),
                    self._log_service.get_project_logs(card.project.id))
            else:
                messagebox.showerror("错误", msg)

        result = show_detail_dialog(self, card.project, stages, logs,
                                   on_move=_handle_move)
        if not result:
            return

        action, data = result
        if action == "edit":
            success, msg = self._project_service.update_project(
                card.project.id,
                company_name=data.get("company_name"),
                system_name=data.get("system_name"),
                cert_number=data.get("cert_number"),
                issue_date=data.get("issue_date"),
                level=data.get("level"),
                deadline=data.get("deadline"),
                notes=data.get("notes"),
                stage_id=data.get("stage_id"),
            )
            if success:
                self._refresh_kanban()
            else:
                messagebox.showerror("错误", msg)

        elif action == "delete":
            success, msg = self._project_service.delete_project(card.project.id)
            if success:
                self._refresh_kanban()
            else:
                messagebox.showerror("错误", msg)
    def _on_card_edit(self, card: ProjectCard):
        """编辑按钮 / 双击卡片 -- 直接打开编辑对话框

        这是卡片双击和编辑按钮的共同入口点，直接打开项目编辑对话框。
        不走详情对话框流程，更快直达编辑。

        Args:
            card: 被双击/被点击编辑的卡片组件
        """
        stages = self._workflow_service.get_all_stages()  # 获取阶段列表（供编辑对话框下拉选择）
        result = show_project_dialog(self, "编辑项目", card.project, stages)  # 打开编辑对话框
        if result:  # 用户确认修改
            success, msg = self._project_service.update_project(
                card.project.id,
                company_name=result.get("company_name"),
                system_name=result.get("system_name"),
                cert_number=result.get("cert_number"),
                issue_date=result.get("issue_date"),
                level=result.get("level"),
                deadline=result.get("deadline"),
                notes=result.get("notes"),
                stage_id=result.get("stage_id"),
            )
            if success:
                self._refresh_kanban()
            else:
                messagebox.showerror("错误", msg)

    def _on_card_move_stage(self, card: ProjectCard, target_stage_id: str):
        """卡片箭头按钮移动项目到目标阶段的处理

        当用户点击卡片上的左箭头或右箭头时触发。
        检查源阶段和目标阶段是否相同（避免无意义调用），
        然后调用项目服务执行移动操作。

        Args:
            card: 被移动的卡片组件
            target_stage_id: 目标阶段的唯一标识符
        """
        # 找到卡片当前所在阶段（源阶段）
        source_stage_id = card.project.stage_id
        if source_stage_id == target_stage_id:
            return  # 源和目标相同，无需移动

        success, msg = self._project_service.move_project(
            card.project.id, target_stage_id,  # 将项目移到目标阶段
        )
        if success:
            self._kanban.move_card_to_column(card, target_stage_id)  # 在UI上执行卡片移动（即时更新，无需全量刷新）
        else:
            messagebox.showerror("错误", msg)

    def _on_card_copy(self, card: ProjectCard):
        """复制项目按钮的事件处理

        读取当前项目的所有字段，创建一份完整副本。
        副本公司名称在原名称后追加" - 副本"后缀，与其他字段保持一致。

        Args:
            card: 被点击复制的卡片组件
        """
        p = card.project  # 源项目
        copy_name = f"{p.company_name} - \u526f\u672c"  # 公司名称 + " - 副本"
        success, msg, _ = self._project_service.create_project(
            company_name=copy_name,
            system_name=p.system_name,
            cert_number=p.cert_number,
            issue_date=p.issue_date,
            level=p.level,
            deadline=p.deadline,
            notes=p.notes,
            stage_id=p.stage_id,
        )
        if success:
            self._refresh_kanban()
        else:
            messagebox.showerror("错误", msg)

    def _on_column_resize(self, stage_id: str, new_width: int):
        """列宽拖拽完成 —— 将新宽度保存到工作流数据

        Args:
            stage_id: 被调整的阶段ID
            new_width: 新的列宽（像素）
        """
        self._workflow_service.update_stage_width(stage_id, new_width)

    def _create_project_folder(self, project):
        """为新建项目创建数据文件夹

        在程序同目录 projects/ 下创建文件夹，命名规则：
        序号-公司名称-系统名称-创建日期(YYMMDD)
        """
        import os
        from datetime import date
        try:
            base = Config.get_data_dir()
            os.makedirs(base, exist_ok=True)
            count = len(self._project_service.get_all_projects())
            date_str = date.today().strftime("%y%m%d")
            cname = (project.company_name or "未命名").replace("/", "_").replace("\\", "_")
            sname = (project.system_name or "").replace("/", "_").replace("\\", "_")
            folder_name = f"{count:03d}-{cname}-{sname}-{date_str}"
            folder_path = os.path.join(base, folder_name)
            os.makedirs(folder_path, exist_ok=True)
        except OSError:
            pass  # 文件夹创建失败不影响主流程

    # ==================== 窗口事件 ====================

    def _on_window_resize(self, event):
        """窗口大小变化时的自适应调整

        Tkinter的pack布局管理器会自动处理组件大小调整，
        此方法作为预留扩展点，可在此添加额外的自适应逻辑。

        Args:
            event: Tkinter的Configure事件对象
        """
        pass  # Tkinter的pack布局会自动处理，可在此添加额外逻辑

    def _on_close(self):
        """窗口关闭前的清理工作

        保存所有数据到JSON文件，然后销毁窗口。
        绑定到窗口的WM_DELETE_WINDOW协议，确保关闭窗口时数据不丢失。
        """
        self._data_service.save()  # 保存所有数据到JSON文件
        self.destroy()  # 销毁Tkinter窗口，退出mainloop

    # ==================== 内部方法 ====================

    def _refresh_kanban(self):
        """刷新看板显示（重新加载所有数据并渲染）

        从服务层获取最新的阶段列表和项目列表，
        调用看板的load_stages方法重建所有列和卡片。
        这是数据变更后统一刷新UI的入口方法。
        """
        stages = self._workflow_service.get_all_stages()  # 获取最新阶段列表
        projects = self._project_service.get_all_projects()  # 获取最新项目列表
        self._kanban.load_stages(stages, projects)  # 重建看板列和卡片显示
