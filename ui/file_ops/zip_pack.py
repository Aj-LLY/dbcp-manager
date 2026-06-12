"""
过程文档 ZIP 打包模块

提供 on_zip_click 函数：
  将项目过程文件按预定义关键词筛选后压缩为 ZIP 归档。
"""

import os
import zipfile
from tkinter import messagebox

from models.project import Project
from ui.file_ops.folder_ops import find_project_folder


# =============================================================================
# on_zip_click - 打包过程文档功能
# =============================================================================

def on_zip_click(project: Project, parent=None, all_projects: list = None):
    """处理"打包过程文档"按钮点击 - 将项目过程文件压缩为 ZIP

    多系统: 扫描根目录(公司级文件) + 各系统子目录，保持目录结构。

    Args:
        project: 项目实体对象
        parent: 父级窗口
        all_projects: 合并卡片的所有项目（用于判断多系统）
    """
    try:
        root = find_project_folder(project)
        if not root or not os.path.isdir(root):
            messagebox.showinfo("提示", "未找到项目文件夹")
            return

        cname = (project.company_name or "未命名").replace("/", "_").replace("\\", "_")
        sname = (project.system_name or "").replace("/", "_").replace("\\", "_")
        is_multi = all_projects and len(all_projects) > 1

        zip_name = f"{cname}-{sname}-过程文档.zip" if not is_multi else f"{cname}-过程文档.zip"
        zip_path = os.path.join(root, zip_name)

        # ---- 构建扫描目录列表 ----
        scan_dirs = [root]
        if is_multi:
            for dname in os.listdir(root):
                dpath = os.path.join(root, dname)
                if os.path.isdir(dpath) and "报告打印" not in dname \
                        and dname != "01-其他归档文件":
                    scan_dirs.append(dpath)

        pack_keywords = [
            "测评调研表", "测评授权书", "风险告知书",
            "项目计划书", "测评方案",
            "首次会议记录", "测评现场记录表",
            "问题汇总", "漏洞扫描报告",
            "项目文档移交清单", "末次会议记录",
        ]

        count = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # --- 第一步：打包匹配关键词的单文件 ---
            for scan_root in scan_dirs:
                for fname in os.listdir(scan_root):
                    fpath = os.path.join(scan_root, fname)
                    if not os.path.isfile(fpath) or fname == zip_name:
                        continue
                    name_no_ext = os.path.splitext(fname)[0]
                    for kw in pack_keywords:
                        if kw in name_no_ext:
                            arcname = os.path.relpath(fpath, root).replace("\\", "/")
                            zf.write(fpath, arcname)
                            count += 1
                            break

            # --- 第二步：打包渗透测试报告目录 ---
            for scan_root in scan_dirs:
                for dname in os.listdir(scan_root):
                    dpath = os.path.join(scan_root, dname)
                    if os.path.isdir(dpath) and "渗透测试报告" in dname:
                        has_files = False
                        for dirpath, _, filenames in os.walk(dpath):
                            for fn in filenames:
                                fp = os.path.join(dirpath, fn)
                                arcname = os.path.relpath(fp, root).replace("\\", "/")
                                zf.write(fp, arcname)
                                count += 1
                                has_files = True
                        if not has_files:
                            arcname = os.path.relpath(dpath, root).replace("\\", "/") + "/"
                            info = zipfile.ZipInfo(arcname)
                            zf.writestr(info, "")
                            count += 1

        if count > 0:
            messagebox.showinfo("打包完成",
                f"已打包 {count} 个文件\n{zip_name}")
        else:
            os.remove(zip_path)
            messagebox.showinfo("提示", "未找到可打包的过程文件")

    except Exception as e:
        messagebox.showerror("错误", f"打包失败: {e}")
