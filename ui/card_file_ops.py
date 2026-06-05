"""
项目卡片文件操作模块 -- 从 project_card.py 提取的独立文件操作函数

本模块是文件操作功能的入口点，实际实现已拆分到 ui.file_ops 子包中：
  - ui.file_ops.folder_ops:    find_project_folder, on_folder_click
  - ui.file_ops.init_project:  on_init_click
  - ui.file_ops.rename:        on_rename_click
  - ui.file_ops.zip_pack:      on_zip_click

on_report_print_click 保留在此文件中（与报告打印对话框耦合较紧）。

向后兼容：所有函数仍可通过 `from ui.card_file_ops import ...` 导入。
"""

# =============================================================================
# 导入区
# =============================================================================

import os          # 文件系统操作
import shutil      # 高级文件操作（复制保留元数据）
from tkinter import messagebox  # 消息弹窗
from datetime import date       # 当前日期

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

def on_report_print_click(project: Project, parent=None):
    """处理"报告打印"按钮点击 - 生成测评报告打印信息并复制相关文件

    完整流程：
      1. 查找项目文件夹（如果找不到则提示并退出）
      2. 弹出 show_report_dialog 编辑确认框，预填项目数据
      3. 用户确认 14 个字段后，查找/创建报告打印子目录
      4. 调用 _create_report_xlsx_data 生成测评报告打印信息.xlsx
      5. 复制相关文件到报告打印目录：
         - "测评授权书"相关文件
         - "风险告知书"相关文件
         - "测评报告-终稿.pdf"（如果有）
         - 过程文档 ZIP（如果有）
      6. 弹窗显示生成结果

    报告打印目录命名：00-{公司}-{系统}-报告打印
    XLSX 文件命名：00-{公司}-{系统}-测评报告打印信息.xlsx

    Args:
        project: 项目实体对象
        parent: 父级窗口（用于对话框的模态绑定）
    """
    try:
        proot = find_project_folder(project)  # 查找项目文件夹根目录
        if not proot or not os.path.isdir(proot):  # 根目录不存在
            messagebox.showinfo("提示", "未找到项目文件夹")
            return

        # ---- 步骤 1: 弹出报告打印编辑确认框 ----
        data = show_report_dialog(
            parent,  # 父窗口
            cname=project.company_name or "",  # 预填公司名称
            sname=project.system_name or "",  # 预填系统名称
            location=(project.location or "").split("-")[0]  # 预填所属地（取省/市前缀）
                if project.location else "",  # 无属地则空
            deadline=project.deadline or date.today().strftime("%Y-%m-%d"),  # 预填日期
        )
        if not data:  # 用户点击了取消
            return

        # 提取用户确认后的关键字段
        cname = data["cname"]  # 客户公司全称
        sname = data["sname"]  # 系统名称
        prefix = f"{cname}-{sname}"  # 文件名前缀

        # ---- 步骤 2: 查找或创建报告打印目录 ----
        report_dir = None  # 报告打印目录路径
        for dname in os.listdir(proot):  # 在项目根目录中查找
            if "报告打印" in dname and os.path.isdir(os.path.join(proot, dname)):
                report_dir = os.path.join(proot, dname)  # 找到已存在的报告打印目录
                break
        if not report_dir:  # 不存在则创建
            report_dir = os.path.join(proot, f"00-{prefix}-报告打印")  # 按标准格式命名
            os.makedirs(report_dir, exist_ok=True)  # 递归创建

        # ---- 步骤 3: 创建测评报告打印信息 XLSX ----
        xlsx_name = f"00-{prefix}-测评报告打印信息.xlsx"  # XLSX 文件名
        xlsx_path = os.path.join(report_dir, xlsx_name)  # XLSX 完整路径
        _create_report_xlsx_data(project, xlsx_path, data, report_dir, proot)  # 生成 XLSX

        # ---- 步骤 4: 复制相关文件到报告打印目录 ----
        copied = 0  # 已复制文件计数

        # 复制"测评授权书"和"风险告知书"相关文件
        copy_keywords = ["测评授权书", "风险告知书"]
        for fname in os.listdir(proot):  # 遍历项目根目录
            fpath = os.path.join(proot, fname)
            if not os.path.isfile(fpath):  # 跳过目录
                continue
            for kw in copy_keywords:  # 遍历复制关键词
                if kw in fname:  # 文件名匹配关键词
                    shutil.copy2(fpath, os.path.join(report_dir, fname))  # 复制（保留元数据）
                    copied += 1  # 计数
                    break  # 匹配一个即处理下一个文件

            # 复制测评报告终稿 PDF
            if "测评报告-终稿" in fname and fname.lower().endswith(".pdf"):  # 必须是 PDF
                shutil.copy2(fpath, os.path.join(report_dir, fname))  # 复制到打印目录
                copied += 1

        # 复制过程文档 ZIP（如果已生成）
        zip_name = f"{cname}-{sname}-过程文档.zip"  # ZIP 文件名
        zip_src = os.path.join(proot, zip_name)  # ZIP 源路径
        if os.path.exists(zip_src):  # ZIP 文件存在
            shutil.copy2(zip_src, os.path.join(report_dir, zip_name))  # 复制
            copied += 1

        # ---- 步骤 5: 显示结果 ----
        messagebox.showinfo("报告打印完成",
            f"已生成 {xlsx_name}\n已复制 {copied} 个文件到报告打印目录")

    except Exception as e:  # 捕获所有异常
        messagebox.showerror("错误", f"报告打印失败: {e}")  # 显示错误
