"""
项目卡片文件操作模块 -- 等保测评进度管理系统

============ 本模块职责 ============
作为 UI 层的文件操作协调器，将各独立子模块（folder_ops、init_project、
rename、zip_pack）的功能统一导出，并额外提供报告打印功能。

============ 架构设计 ============
  设计原则 #1（分层）：
    - 本模块属于 UI 层控制器，负责协调文件操作与对话框之间的交互
    - 不直接处理数据层逻辑（数据读写由 models 层负责）
    - 文件操作的底层实现分散在 ui/file_ops/ 各子模块中

  设计原则 #7（显式异常处理）：
    - 异常分类处理：关键失败记录日志并弹窗提示，非关键失败静默处理
    - 使用 _logger 区分调试日志和用户提示

============ 导出列表 ============
  从子模块重新导出的函数（保持向后兼容）：
    - find_project_folder / on_folder_click  → 来自 folder_ops
    - on_init_click                          → 来自 init_project
    - on_rename_click                        → 来自 rename
    - on_zip_click                           → 来自 zip_pack

  本模块定义：
    - on_report_print_click                  → 报告打印（5 步流程）
"""
import logging    # 日志模块：使用 debug 级别记录跳过的文件等非关键信息
import os         # 操作系统接口：目录遍历、路径拼接
import shutil     # 文件操作高级工具：复制文件
from tkinter import messagebox  # 消息框：通知用户打印结果
from datetime import date       # 日期模块：获取今天日期作为截止日期默认值

# 模块级日志实例（使用模块名作为 logger 名称，便于日志分层过滤）
_logger = logging.getLogger(__name__)

# ---- 模型层 ----
from models.project import Project  # 项目实体类

# ---- 报告打印对话框 ----
from ui.dialog_report_print import (
    show_report_dialog,              # 报告打印前的编辑确认对话框（14 个可编辑字段）
    _create_report_xlsx,             # 创建 XLSX 文件的基础结构（写入固定表头）
    _create_report_xlsx_data,        # 根据用户编辑的数据填充 XLSX 内容
)

# ---- 从子模块重新导出（保持向后兼容） ----
# 其他模块可以直接从 card_file_ops 导入这些函数，无需关心底层子模块路径
from ui.file_ops.folder_ops import find_project_folder, on_folder_click
from ui.file_ops.init_project import on_init_click
from ui.file_ops.rename import on_rename_click
from ui.file_ops.zip_pack import on_zip_click


# =============================================================================
# on_report_print_click - 报告打印入口函数
# =============================================================================

def on_report_print_click(project: Project, parent=None, all_projects: list = None):
    """处理"报告打印"按钮点击：生成测评报告打印信息并汇总相关文件。

    完整的 5 步报告打印流程：
      步骤 1 — 编辑确认对话框：弹出 14 字段编辑框，用户确认或修改打印信息
      步骤 2 — 定位报告打印目录：查找或创建 00-{前缀}-报告打印 目录
      步骤 3 — 复制附件文件：将授权书、告知书、基本情况表、PDF 报告
              以及过程文档 ZIP 复制到报告打印目录
      步骤 4 — 生成 XLSX：创建 00-{前缀}-测评报告打印信息.xlsx 文件
      步骤 5 — 弹窗报告结果：显示生成的文件名和复制的文件数量

    多系统模式下的特殊处理：
      - 系统名称：换行拼接所有子系统的系统名（编辑框显示用 \n 分隔）
      - 所属地：取第一个项目的省级名称（"省-市"中"-"前面的部分）
      - 扫描范围：根目录（公司级文件）+ 各系统子目录
      - ZIP 文件名：不含系统名（{公司名}-过程文档.zip）

    Args:
        project: 项目实体对象，提供公司名称、系统名称、所属地等信息。
        parent: 父级 Tkinter 窗口引用（传入对话框作为模态父窗口）。
        all_projects: 多系统合并时所有关联项目列表，用于：
                      ① 判断多系统模式
                      ② 汇总所有系统名称
                      ③ 确定扫描目录范围

    Returns:
        None: 所有结果通过 messagebox 弹窗展示。
    """
    try:
        # ========== 前置：定位项目文件夹 ==========
        proot = find_project_folder(project)
        if not proot or not os.path.isdir(proot):
            messagebox.showinfo("提示", "未找到项目文件夹")
            return

        is_multi = all_projects and len(all_projects) > 1

        # ---- 构建显示用的字段值 ----
        # 多系统：系统名称换行拼接所有子系统的系统名
        # 单系统：直接取当前项目的系统名
        if is_multi:
            sname_display = "\n".join(p.system_name or "" for p in all_projects)
        else:
            sname_display = project.system_name or ""

        # 所属地：取 "省-市" 中的省级名称（"广东-广州" → "广东"）
        location_display = (project.location or "").split("-")[0] \
            if project.location else ""

        # ==================================================================
        # 步骤 1：弹出编辑确认对话框
        # ==================================================================
        # 用户在此对话框中可编辑公司名、系统名、所属地、截止日期等 14 个字段
        # 返回 data 字典包含所有编辑后的值；用户取消时返回 None 或空字典
        data = show_report_dialog(
            parent,
            cname=project.company_name or "",
            sname=sname_display,
            location=location_display,
            deadline=project.deadline or date.today().strftime("%Y-%m-%d"),
        )
        if not data:
            return  # 用户取消了编辑，终止流程

        # 用户可能在对话框中修改了名称，需要同时保留编辑后的名称和原始名称
        cname = data["cname"]  # 编辑后的公司名（用于 XLSX 和目录命名）
        sname = data["sname"]  # 编辑后的系统名
        # 原始项目名（路径安全版本），用于查找 ZIP 文件（对话框不能修改 ZIP 文件名）
        orig_cname = (project.company_name or "").replace("/", "_").replace("\\", "_")
        orig_sname = (project.system_name or "").replace("/", "_").replace("\\", "_")
        # 目录前缀：多系统仅用公司名，单系统用 公司-系统
        prefix = cname if is_multi else f"{cname}-{sname}"

        # ---- 构建扫描目录列表 ----
        # 多系统：根目录 + 各系统子目录；单系统：仅根目录
        scan_dirs = [proot]
        if is_multi:
            for dname in os.listdir(proot):
                dpath = os.path.join(proot, dname)
                if os.path.isdir(dpath) and "报告打印" not in dname \
                        and dname != "01-其他归档文件":
                    scan_dirs.append(dpath)

        # ==================================================================
        # 步骤 2：查找或创建报告打印目录
        # ==================================================================
        # 先查找已有的报告打印目录（目录名含"报告打印"关键词）
        # 如果不存在则创建标准命名的报告打印目录
        report_dir = None
        for dname in os.listdir(proot):
            if "报告打印" in dname and os.path.isdir(os.path.join(proot, dname)):
                report_dir = os.path.join(proot, dname)
                break
        if not report_dir:
            # 创建新目录：00-{前缀}-报告打印（编号 00 表示辅助目录）
            report_dir = os.path.join(proot, f"00-{prefix}-报告打印")
            os.makedirs(report_dir, exist_ok=True)

        # ==================================================================
        # 步骤 3：复制附件文件到报告打印目录
        # ==================================================================
        copied = 0  # 成功复制的文件数

        # 需要复制的附件关键词（用于匹配文件名）
        # - 基本情况表：被测系统基本信息登记表
        # - 测评授权书：客户签署的测评授权文件
        # - 风险告知书：客户签署的风险知情确认
        # - 放弃工具测试声明：如客户要求放弃漏洞扫描等工具测试时签署
        copy_keywords = ["基本情况表", "测评授权书", "风险告知书", "放弃工具测试声明"]

        for scan_root in scan_dirs:
            for fname in os.listdir(scan_root):
                fpath = os.path.join(scan_root, fname)
                if not os.path.isfile(fpath):
                    continue  # 跳过目录

                # 匹配附件关键词
                for kw in copy_keywords:
                    if kw in fname:
                        try:
                            shutil.copy(fpath, os.path.join(report_dir, fname))
                            copied += 1
                        except (PermissionError, shutil.SameFileError):
                            # 权限不足（文件被锁定）或源和目标相同：记录调试日志后跳过
                            _logger.debug("跳过文件(锁定/同文件): %s", fpath)
                        break  # 一个文件只匹配一个关键词

                # PDF 格式的测评报告也要复制（最终版报告通常为 PDF）
                if "测评报告" in fname and fname.lower().endswith(".pdf"):
                    try:
                        shutil.copy(fpath, os.path.join(report_dir, fname))
                        copied += 1
                    except (PermissionError, shutil.SameFileError):
                        _logger.debug("跳过文件(锁定/同文件): %s", fpath)

        # ---- 复制过程文档 ZIP ----
        # ZIP 文件名使用原始项目名（用户在编辑框中修改的名称不影响 ZIP 查找）
        zip_name = f"{orig_cname}-过程文档.zip" if is_multi else f"{orig_cname}-{orig_sname}-过程文档.zip"
        for scan_root in scan_dirs:
            zip_src = os.path.join(scan_root, zip_name)
            if os.path.exists(zip_src):
                try:
                    shutil.copy(zip_src, os.path.join(report_dir, zip_name))
                    copied += 1
                except (PermissionError, shutil.SameFileError):
                    _logger.debug("跳过 ZIP(锁定/同文件): %s", zip_src)

        # ==================================================================
        # 步骤 4：创建测评报告打印信息 XLSX
        # ==================================================================
        xlsx_name = f"00-{prefix}-测评报告打印信息.xlsx"
        xlsx_path = os.path.join(report_dir, xlsx_name)
        # 调用 dialog_report_print 模块的函数生成 XLSX 文件
        # 传入编辑后的 data、当前项目、报告目录、根目录等上下文信息
        _create_report_xlsx_data(project, xlsx_path, data, report_dir, proot,
                                 all_projects=all_projects)

        # ==================================================================
        # 步骤 5：弹窗显示结果
        # ==================================================================
        messagebox.showinfo("报告打印完成",
            f"已生成 {xlsx_name}\n已复制 {copied} 个文件到报告打印目录")

    except Exception as e:
        # 关键异常：记录完整堆栈到日志，同时向用户展示错误提示
        _logger.exception("报告打印失败")
        messagebox.showerror("错误", f"报告打印失败: {e}")
