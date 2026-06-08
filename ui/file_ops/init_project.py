"""
项目初始化模块

提供 on_init_click 函数：
  创建标准子目录（01-其他归档文件、00-报告打印）和保密承诺书模板。
"""

import os
import shutil
from tkinter import messagebox

from models.project import Project
from utils.config import Config
from ui.file_ops.folder_ops import find_project_folder


# =============================================================================
# on_init_click - 项目初始化
# =============================================================================

def on_init_click(project: Project, parent=None):
    """项目初始化：创建标准子目录和保密承诺书模板

    创建内容：
      1. "01-其他归档文件" 子目录
      2. "00-{公司}-{系统}-报告打印" 子目录
      3. "02-{公司}-{系统}-保密承诺书.docx" 模板文件（从模板复制并替换公司名和日期）

    Args:
        project: 项目实体对象
        parent: 父级窗口（用于消息弹窗的模态绑定）
    """
    try:
        root = find_project_folder(project)
        if not root or not os.path.isdir(root):
            messagebox.showinfo("提示", "未找到项目文件夹")
            return
        cname = (project.company_name or "未命名").replace("/", "_").replace("\\", "_")
        sname = (project.system_name or "").replace("/", "_").replace("\\", "_")
        created = []; existed = []
        # 01-其他归档文件
        dname = "01-其他归档文件"
        dpath = os.path.join(root, dname)
        if not os.path.exists(dpath):
            os.makedirs(dpath, exist_ok=True); created.append(dname)
        else:
            existed.append(dname)
        # 02-保密承诺书（单系统加系统名，多系统只有公司名）
        nda_name = f"02-{cname}-{sname}-保密承诺书.docx" if sname else f"02-{cname}-保密承诺书.docx"
        nda_path = os.path.join(root, nda_name)
        if os.path.exists(nda_path):
            existed.append(nda_name)
        else:
            try:
                tpl = os.path.join(Config.get_data_dir(), "templates", "02-保密承诺书模板.docx")
                if os.path.exists(tpl):
                    import docx
                    shutil.copy2(tpl, nda_path)
                    doc = docx.Document(nda_path)
                    company = project.company_name or ""
                    create_date = project.created_at[:10] if project.created_at else ""
                    # 替换公司名: 逐run保留格式
                    for p in doc.paragraphs:
                        for run in p.runs:
                            if "XX公司" in run.text or "xx公司" in run.text:
                                run.text = run.text.replace("XX公司", company).replace("xx公司", company)
                                break
                    # 清除 split 的 "XX"+"公司" run 对
                    for p in doc.paragraphs:
                        for j in range(len(p.runs) - 1):
                            if p.runs[j].text.strip() == "XX" and p.runs[j+1].text.strip() == "公司":
                                p.runs[j].text = company; p.runs[j+1].text = ""
                    # 替换日期: 保留每个run格式, 仅替换"XX"
                    if create_date:
                        parts = create_date.split("-")
                        if len(parts) == 3:
                            y, m, d = parts[0], f"{int(parts[1]):02d}", f"{int(parts[2]):02d}"
                            for table in doc.tables:
                                for row in table.rows:
                                    for cell in row.cells:
                                        for p in cell.paragraphs:
                                            rs = p.runs
                                            if len(rs) >= 6 and all(rs[k].text.strip() == v for k, v in [(0,"XX"),(2,"XX"),(4,"XX")]):
                                                rs[0].text = y; rs[2].text = m; rs[4].text = d
                                                break
                    doc.save(nda_path)
                    created.append(nda_name)
            except Exception:
                pass
        # 弹窗报告
        lines = []
        if created:
            lines.append("--- 已创建 ---")
            lines.extend(f"  + {x}" for x in created)
        if existed:
            lines.append("--- 已存在 ---")
            lines.extend(f"  = {x}" for x in existed)
        messagebox.showinfo("初始化完成", "\n".join(lines) if lines else "无需初始化")
    except Exception as e:
        messagebox.showerror("错误", f"初始化失败: {e}")
