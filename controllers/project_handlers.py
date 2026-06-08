"""
项目事件处理函数模块 - 从 MainWindow 中抽取的项目 CRUD 相关事件处理器

本模块包含与项目卡片操作相关的所有事件处理函数，采用函数式风格：
  - 每个函数以 MainWindow 实例作为第一个参数（main_window）
  - 通过 main_window 访问所有服务层和 UI 组件（._project_service 等）

主要功能：
  1. 项目增删改查（新增、删除、编辑、复制）
  2. 卡片交互（选中、详情、阶段移动、列宽调整）
  3. 项目文件夹结构创建与 NDA 模板生成
"""

# =============================================================================
# 导入区
# =============================================================================

import os  # 操作系统接口，用于创建目录和处理路径
import shutil  # 文件操作工具，用于复制模板文件
import tkinter as tk  # Python 标准 GUI 库
from tkinter import messagebox  # 消息弹窗组件
from datetime import date  # 日期类，用于生成日期字符串

from models.project import Project  # 项目实体类（用于类型标注）
from ui.project_card import ProjectCard  # 项目卡片组件（用于类型标注）
from ui.project_dialog import show_project_dialog  # 项目编辑对话框便捷函数
from ui.detail_dialog import show_detail_dialog  # 项目详情对话框便捷函数
from utils.config import Config  # 全局配置类


# =============================================================================
# 工具栏事件处理函数 - 响应顶部工具栏各按钮的点击
# =============================================================================

def on_add_project(main_window):
    """处理"新增项目"按钮点击事件

    执行流程：
      1. 检查是否有已配置的流程阶段（无阶段时无法创建项目，提示用户先配置）
      2. 打开新增项目对话框，预填当前所有流程阶段供下拉选择
      3. 用户填写并确认后，通过 ProjectService 创建项目实体
      4. 创建成功后自动建立项目文件夹结构，刷新看板显示

    数据流：
      用户输入 -> show_project_dialog() 返回 dict -> ProjectService.create_project() -> 写入 JSON
    """
    stages = main_window._workflow_service.get_all_stages()  # 从流程服务获取所有已配置的阶段列表
    if not stages:  # 如果没有任何流程阶段
        messagebox.showwarning("提示", "请先配置流程阶段")  # 弹窗提示用户需要先配置阶段
        return  # 中止操作，不打开对话框

    result = show_project_dialog(main_window, "新增项目", stages=stages)  # 打开新增项目对话框，传入阶段列表
    if result:  # 用户点击了"确认"按钮（非取消），result 为包含所有表单字段的字典
        # 调用项目服务创建项目，传入用户在对话框中填写的各字段值
        success, msg, project = main_window._project_service.create_project(
            company_name=result["company_name"],  # 客户公司名称
            system_name=result["system_name"],  # 被测系统名称
            cert_number=result["cert_number"],  # 证书备案编号
            issue_date=result.get("issue_date", ""),  # 证书签发日期（可选）
            level=result.get("level", ""),  # 系统安全保护等级（可选）
            location=result.get("location", ""),  # 项目所属地（可选）
            deadline=result["deadline"],  # 项目截止交付日期（必填）
            notes=result["notes"],  # 备注信息
            stage_id=result["stage_id"],  # 初始流程阶段 ID
        )
        if success:
            user_folder = result.get("folder_path", "").strip()
            if user_folder and os.path.isdir(user_folder):
                # 用户指定了已有目录，直接使用
                project.folder_path = user_folder
                main_window._data_service.update_project(project.id, {"folder_path": user_folder})
            else:
                create_project_folder(main_window, project)
            main_window._refresh_kanban()
        else:
            messagebox.showerror("错误", msg)  # 创建失败时弹窗显示错误原因


def on_delete_selected(main_window):
    """处理"删除项目"按钮点击事件

    执行流程：
      1. 获取当前看板中选中的项目 ID
      2. 如果未选中任何卡片，提示用户先选择项目
      3. 显示二次确认对话框（防止误删）
      4. 确认后通过 ProjectService 执行永久删除
      5. 删除成功后刷新看板
    """
    project_id = main_window._kanban.get_selected_project_id()  # 从看板获取当前选中卡片的项目 ID
    if not project_id:  # 没有任何卡片被选中
        messagebox.showinfo("提示", "请先在卡片上点击选择要删除的项目")  # 提示用户先选择
        return  # 中止操作

    project = main_window._project_service.get_project_by_id(project_id)  # 根据 ID 获取项目对象（用于显示名称）
    if not project:  # 防御性检查：项目可能已被其他操作删除
        return

    # 二次确认对话框：显示项目名称，提醒用户此操作不可撤销
    if messagebox.askyesno("确认删除",
                           f"确定要永久删除项目\u300c{project.name}\u300d吗？\n\n"
                           "此操作不可撤销！"):  # \u300c = 「，\u300d = 」
        success, msg = main_window._project_service.delete_project(project_id)  # 执行项目删除操作
        if success:  # 删除成功
            main_window._refresh_kanban()  # 刷新看板，移除已删除的项目卡片
        else:
            messagebox.showerror("错误", msg)  # 删除失败时弹窗显示错误信息


# =============================================================================
# 看板事件处理函数 - 响应看板中卡片的交互操作
# =============================================================================

def on_card_selected(main_window, card: ProjectCard | None):
    """处理卡片选中状态变化事件

    当用户单击看板中的卡片时触发。可用于扩展功能，如：
      - 更新状态栏显示当前选中项目的信息
      - 启用/禁用依赖于选中状态的操作按钮

    当前为空实现，预留扩展点。

    Args:
        card: 当前选中的卡片组件实例，或 None（表示取消选中/点击空白区域）
    """
    pass  # 预留扩展：可在此添加状态栏更新、右键菜单等逻辑


def pick_project_from_card(main_window, card: ProjectCard) -> Project | None:
    """从合并卡片中选择单个项目。单项目直接返回, 多项目弹出选择列表。"""
    projects = card.projects or [card.project]
    if len(projects) == 1:
        return projects[0]
    dlg = tk.Toplevel(main_window)
    dlg.title("选择系统")
    dlg.geometry("320x250")
    dlg.configure(bg="#ffffff")
    dlg.grab_set()
    tk.Label(dlg, text="请选择要操作的系统:", bg="#ffffff",
             font=("Microsoft YaHei", 11, "bold")).pack(pady=(15, 10))
    lb = tk.Listbox(dlg, font=("Microsoft YaHei", 10), selectmode="single")
    lb.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
    for p in projects:
        lb.insert(tk.END, p.system_name or p.name)
    lb.selection_set(0)
    result = {"project": None}
    def _ok():
        sel = lb.curselection()
        if sel:
            result["project"] = projects[sel[0]]
        dlg.destroy()
    btn_frame = tk.Frame(dlg, bg="#f0f2f5")
    btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
    tk.Frame(btn_frame, bg="#d0d5dd", height=1).pack(fill=tk.X)
    inner = tk.Frame(btn_frame, bg="#f0f2f5")
    inner.pack(fill=tk.X, padx=16, pady=8)
    tk.Button(inner, text="取消", command=dlg.destroy,
        bg="#ffffff", fg="#2c3e50", cursor="hand2").pack(side=tk.RIGHT, padx=(10,0))
    tk.Button(inner, text="确定", command=_ok,
        bg="#3498db", fg="white", cursor="hand2").pack(side=tk.RIGHT)
    dlg.bind("<Return>", lambda e: _ok())
    main_window.wait_window(dlg)
    return result["project"]


def on_card_detail(main_window, card: ProjectCard):
    """处理卡片详情按钮。多系统时直接展示所有系统。"""
    project = card.projects[0] if card.projects else card.project
    all_projects = card.projects if card.projects and len(card.projects) > 1 else None
    stages = main_window._workflow_service.get_all_stages()
    logs = main_window._log_service.get_project_logs(project.id)

    def _handle_move(target_stage_id, dialog):
        success, msg = main_window._project_service.move_project(project.id, target_stage_id)
        if success:
            main_window._refresh_kanban()
            upd = main_window._project_service.get_project_by_id(project.id)
            dialog.refresh_data(upd,
                main_window._workflow_service.get_all_stages(),
                main_window._log_service.get_project_logs(project.id))
        else:
            messagebox.showerror("错误", msg)

    result = show_detail_dialog(main_window, project, stages, logs,
                               on_move=_handle_move, all_projects=all_projects)
    if not result:
        return

    action, data = result
    if action == "edit":
        success, msg = main_window._project_service.update_project(
            project.id, company_name=data.get("company_name"),
            system_name=data.get("system_name"), cert_number=data.get("cert_number"),
            issue_date=data.get("issue_date"), level=data.get("level"),
            location=data.get("location"), deadline=data.get("deadline"),
            notes=data.get("notes"), stage_id=data.get("stage_id"),
            folder_path=data.get("folder_path"),
        )
        if success: main_window._refresh_kanban()
        else: messagebox.showerror("错误", msg)
    elif action == "delete":
        success, msg = main_window._project_service.delete_project(project.id)
        if success: main_window._refresh_kanban()
        else: messagebox.showerror("错误", msg)


def on_card_edit(main_window, card: ProjectCard):
    """处理卡片编辑/双击。多系统时编辑当前项目，表格展示所有系统。"""
    project = card.projects[0] if card.projects else card.project
    all_proj = card.projects if card.projects and len(card.projects) > 1 else None
    stages = main_window._workflow_service.get_all_stages()
    result = show_project_dialog(main_window, "编辑项目", project, stages, all_projects=all_proj)
    if result:
        success, msg = main_window._project_service.update_project(
            project.id, company_name=result.get("company_name"),
            system_name=result.get("system_name"), cert_number=result.get("cert_number"),
            issue_date=result.get("issue_date"), level=result.get("level"),
            location=result.get("location"), deadline=result.get("deadline"),
            notes=result.get("notes"), stage_id=result.get("stage_id"),
            folder_path=result.get("folder_path"),
        )
        if success: main_window._refresh_kanban()
        else: messagebox.showerror("错误", msg)


def on_card_move_stage(main_window, card: ProjectCard, target_stage_id: str):
    """处理卡片左箭头/右箭头的阶段移动事件

    当用户点击卡片上的 ◀（左箭头）或 ▶（右箭头）时触发。
    左箭头将项目移到上一阶段，右箭头将项目移到下一阶段。

    先执行防御性检查：如果源阶段和目标阶段相同（用户在边界处误点），直接返回。
    成功后直接在 UI 上移动卡片，无需全量刷新看板（性能优化）。

    Args:
        card: 被操作的项目卡片组件
        target_stage_id: 目标阶段的唯一标识符（由 KanbanBoard 计算得出）
    """
    source_stage_id = card.project.stage_id
    if source_stage_id == target_stage_id:
        return
    # 移动合并卡片中的所有项目
    projects = card.projects or [card.project]
    for p in projects:
        main_window._project_service.move_project(p.id, target_stage_id)
    main_window._kanban.move_card_to_column(card, target_stage_id)


def on_card_copy(main_window, card: ProjectCard):
    """处理卡片"复制"按钮点击事件 - 创建当前项目的完整副本

    复制逻辑：
      - 读取源项目的所有业务字段（公司名称、系统名称、编号、等级等）
      - 公司名称在原值后追加 " - 副本" 后缀以区分原项目
      - 通过 ProjectService.create_project() 创建新项目实体
      - 新项目与源项目处于同一流程阶段

    Args:
        card: 被点击"复制"按钮的项目卡片组件
    """
    for p in (card.projects or [card.project]):
        copy_name = f"{p.company_name} - \u526f\u672c"
        main_window._project_service.create_project(
            company_name=copy_name, system_name=p.system_name,
            cert_number=p.cert_number, issue_date=p.issue_date,
            level=p.level, location=p.location,
            deadline=p.deadline, notes=p.notes, stage_id=p.stage_id,
        )
    main_window._refresh_kanban()


def on_column_resize(main_window, stage_id: str, new_width: int):
    """处理列宽拖拽完成事件 - 保存调整后的列宽到持久化数据

    当用户拖拽看板列右侧的分隔手柄调整列宽后触发。
    将新宽度通过 WorkflowService 持久化保存，下次启动时自动恢复。

    Args:
        stage_id: 被调整宽度列对应的阶段 ID
        new_width: 新的列宽值（单位：像素）
    """
    main_window._workflow_service.update_stage_width(stage_id, new_width)  # 保存新列宽到数据服务


# =============================================================================
# 项目文件夹结构创建函数
# =============================================================================

def create_project_folder(main_window, project):
    """为新建项目创建完整的文件目录结构

    在程序数据目录下创建以公司名+系统名+日期命名的文件夹，
    并初始化以下子目录：
      - 01-其他归档文件/         # 存放杂项归档材料
      - 00-{公司}-{系统}-报告打印/  # 存放打印版报告
      - 13-{公司}-{系统}-渗透测试报告/  # 存放渗透测试相关文件

    文件夹命名规则：
      格式：{序号}-{公司简称}-{系统简称}-{年月日}
      序号：当前项目总数（自动递增）
      日期：创建当日（格式 YYMMDD）

    创建成功后，将文件夹路径保存到 project 对象并持久化到 JSON 文件。

    Args:
        project: 新创建的项目实体对象（包含公司名称、系统名称等信息）
    """
    try:
        base = Config.get_data_dir()  # 获取程序数据根目录路径
        count = len(main_window._project_service.get_all_projects())  # 当前项目总数（含刚创建的）
        date_str = date.today().strftime("%y%m%d")  # 当日日期，如 "260603"（年月日格式）
        # 清理公司名称中的非法字符（路径分隔符）
        cname = (project.company_name or "未命名").replace("/", "_").replace("\\", "_")
        # 清理系统名称中的非法字符
        sname = (project.system_name or "").replace("/", "_").replace("\\", "_")
        # 组装文件夹名称：序号-公司名-系统名-日期
        folder_name = f"{count:03d}-{cname}-{sname}-{date_str}"
        root = os.path.join(base, folder_name)  # 拼接完整文件夹路径
        os.makedirs(root, exist_ok=True)  # 递归创建文件夹目录（exist_ok=True 避免重复创建报错）

        # 定义需要创建的子目录列表
        subdirs = [
            "01-其他归档文件",
            f"00-{cname}-{sname}-报告打印",
        ]
        for d in subdirs:
            os.makedirs(os.path.join(root, d), exist_ok=True)

        # 生成保密承诺书模板（替换年份和公司名称）
        generate_nda_template(main_window, root, cname, project.company_name or "未命名")

        # 持久化文件夹路径
        project.folder_path = root  # 设置项目对象的文件夹路径属性
        main_window._data_service.update_project(project.id, {"folder_path": root})  # 持久化到 JSON
    except OSError:
        pass


def generate_nda_template(main_window, root, cname_clean, company_name):
    """生成保密承诺书模板，替换公司名称和日期。

    Args:
        root: 项目文件夹根路径
        cname_clean: 清理后的公司名称（用于文件名）
        company_name: 原始公司名称（用于文档内容替换）
    """
    try:
        template_path = os.path.join(Config.get_data_dir(), "templates", "02-保密承诺书模板.docx")
        if not os.path.exists(template_path):
            return
        dest_name = f"02-{cname_clean}-{company_name}-保密承诺书.docx" if company_name else f"02-{cname_clean}-保密承诺书.docx"
        dest_path = os.path.join(root, dest_name)
        if os.path.exists(dest_path):
            return
        shutil.copy2(template_path, dest_path)
        import docx
        from datetime import datetime
        doc = docx.Document(dest_path)
        # 替换公司名: 逐run保留格式
        for p in doc.paragraphs:
            for run in p.runs:
                if "XX公司" in run.text or "xx公司" in run.text:
                    run.text = run.text.replace("XX公司", company_name).replace("xx公司", company_name)
                    break
        # 清除 split 的 "XX"+"公司" run 对
        for p in doc.paragraphs:
            for j in range(len(p.runs) - 1):
                if p.runs[j].text.strip() == "XX" and p.runs[j+1].text.strip() == "公司":
                    p.runs[j].text = company_name; p.runs[j+1].text = ""
        # 替换日期: 保留每个run格式, 仅替换"XX"
        now = datetime.now()
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        rs = p.runs
                        if len(rs) >= 6 and all(rs[k].text.strip() == v for k, v in [(0,"XX"),(2,"XX"),(4,"XX")]):
                            rs[0].text = str(now.year)
                            rs[2].text = f"{now.month:02d}"
                            rs[4].text = f"{now.day:02d}"
                            break
        doc.save(dest_path)
    except Exception:
        pass
