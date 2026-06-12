"""
项目卡片文件操作模块

原则 #1（分层）：本模块为 UI 层控制器，协调文件操作和对话框。
原则 #7（显式）：异常分类处理，关键失败不静默吞掉。
"""
import logging
import os
import shutil
from tkinter import messagebox
from datetime import date

_logger = logging.getLogger(__name__)

# ---- 模型层 ----
from models.project import Project  # 项目实体类

# ---- 报告打印对话框 ----
from ui.dialog_report_print import (
    show_report_dialog,         # 报告打印前的编辑确认对话框（14 个可编辑字段）
    _create_report_xlsx,        # 创建 XLSX 基础结构
    _create_report_xlsx_data,   # 根据编辑框数据创建 XLSX
)

# ---- 从子模块重新导出（向后兼容） ----
from ui.file_ops.folder_ops import find_project_folder, on_folder_click
from ui.file_ops.init_project import on_init_click
from ui.file_ops.rename import on_rename_click
from ui.file_ops.zip_pack import on_zip_click


# =============================================================================
# on_report_print_click - 报告打印功能
# =============================================================================

def on_report_print_click(project: Project, parent=None, all_projects: list = None):
    """处理"报告打印"按钮点击 - 生成测评报告打印信息并复制相关文件

    多系统: 扫描根目录(公司级) + 各系统子目录，汇总所有系统的授权书、报告等文件。

    Args:
        project: 项目实体对象
        parent: 父级窗口
        all_projects: 合并卡片的所有项目（用于判断多系统）
    """
    try:
        proot = find_project_folder(project)
        if not proot or not os.path.isdir(proot):
            messagebox.showinfo("提示", "未找到项目文件夹")
            return

        is_multi = all_projects and len(all_projects) > 1

        # 多系统: 汇总所有系统名（所属地取第一个系统即可）
        if is_multi:
            sname_display = "\n".join(p.system_name or "" for p in all_projects)
        else:
            sname_display = project.system_name or ""
        location_display = (project.location or "").split("-")[0] \
            if project.location else ""

        # ---- 步骤 1: 弹出报告打印编辑确认框 ----
        data = show_report_dialog(
            parent,
            cname=project.company_name or "",
            sname=sname_display,
            location=location_display,
            deadline=project.deadline or date.today().strftime("%Y-%m-%d"),
        )
        if not data:
            return

        cname = data["cname"]
        sname = data["sname"]
        # 原始项目名用于 ZIP 查找（对话框可能编辑了名称）
        orig_cname = (project.company_name or "").replace("/", "_").replace("\\", "_")
        orig_sname = (project.system_name or "").replace("/", "_").replace("\\", "_")
        prefix = cname if is_multi else f"{cname}-{sname}"

        # ---- 构建扫描目录列表 ----
        scan_dirs = [proot]
        if is_multi:
            for dname in os.listdir(proot):
                dpath = os.path.join(proot, dname)
                if os.path.isdir(dpath) and "报告打印" not in dname \
                        and dname != "01-其他归档文件":
                    scan_dirs.append(dpath)

        # ---- 步骤 2: 查找或创建报告打印目录 ----
        report_dir = None
        for dname in os.listdir(proot):
            if "报告打印" in dname and os.path.isdir(os.path.join(proot, dname)):
                report_dir = os.path.join(proot, dname)
                break
        if not report_dir:
            report_dir = os.path.join(proot, f"00-{prefix}-报告打印")
            os.makedirs(report_dir, exist_ok=True)

        # ---- 步骤 3: 先复制附件文件到报告打印目录 ----
        copied = 0
        copy_keywords = ["基本情况表", "测评授权书", "风险告知书", "放弃工具测试声明"]
        for scan_root in scan_dirs:
            for fname in os.listdir(scan_root):
                fpath = os.path.join(scan_root, fname)
                if not os.path.isfile(fpath):
                    continue
                for kw in copy_keywords:
                    if kw in fname:
                        try:
                            shutil.copy(fpath, os.path.join(report_dir, fname))
                            copied += 1
                        except (PermissionError, shutil.SameFileError):
                            _logger.debug("跳过文件(锁定/同文件): %s", fpath)
                        break
                if "测评报告" in fname and fname.lower().endswith(".pdf"):
                    try:
                        shutil.copy(fpath, os.path.join(report_dir, fname))
                        copied += 1
                    except (PermissionError, shutil.SameFileError):
                        _logger.debug("跳过文件(锁定/同文件): %s", fpath)

        # 复制过程文档 ZIP
        zip_name = f"{orig_cname}-过程文档.zip" if is_multi else f"{orig_cname}-{orig_sname}-过程文档.zip"
        for scan_root in scan_dirs:
            zip_src = os.path.join(scan_root, zip_name)
            if os.path.exists(zip_src):
                try:
                    shutil.copy(zip_src, os.path.join(report_dir, zip_name))
                    copied += 1
                except (PermissionError, shutil.SameFileError):
                    _logger.debug("跳过 ZIP(锁定/同文件): %s", zip_src)

        # ---- 步骤 4: 创建测评报告打印信息 XLSX ----
        xlsx_name = f"00-{prefix}-测评报告打印信息.xlsx"
        xlsx_path = os.path.join(report_dir, xlsx_name)
        _create_report_xlsx_data(project, xlsx_path, data, report_dir, proot,
                                 all_projects=all_projects)

        # ---- 步骤 5: 显示结果 ----
        messagebox.showinfo("报告打印完成",
            f"已生成 {xlsx_name}\n已复制 {copied} 个文件到报告打印目录")

    except Exception as e:
        _logger.exception("报告打印失败")
        messagebox.showerror("错误", f"报告打印失败: {e}")
