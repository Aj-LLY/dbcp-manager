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

def on_zip_click(project: Project, parent=None):
    """处理"打包过程文档"按钮点击 - 将项目过程文件压缩为 ZIP

    打包策略：
      1. 查找项目文件夹
      2. 创建 ZIP 文件（命名格式：{公司}-{系统}-过程文档.zip）
      3. 按预定义的关键词列表筛选需要打包的文件：
         - 保密承诺书、测评调研表、测评授权书、风险告知书
         - 项目计划书、测评方案、首次会议记录、测评现场记录表
         - 问题汇总、漏洞扫描报告、项目文档移交清单、末次会议记录
         - 服务情况评价表、报备表
      4. 特殊处理"渗透测试报告"目录：
         - 如果目录非空：递归打包所有文件（保持目录结构）
         - 如果目录为空：添加空目录条目
      5. 成功打包后弹窗提示；无可打包文件时删除空 ZIP

    排除项：
      - 测评报告-终稿（不入过程文档包）
      - 报告打印相关文件
      - 其他归档文件

    Args:
        project: 项目实体对象
        parent: 父级窗口（用于消息弹窗的模态绑定）
    """
    try:
        root = find_project_folder(project)  # 查找项目文件夹路径
        if not root or not os.path.isdir(root):  # 文件夹不存在
            messagebox.showinfo("提示", "未找到项目文件夹")
            return

        # 构建 ZIP 文件名
        cname = project.company_name or "未命名"  # 公司名（取不到用"未命名"）
        sname = project.system_name or ""  # 系统名
        zip_name = f"{cname}-{sname}-过程文档.zip"  # ZIP 文件名格式
        zip_path = os.path.join(root, zip_name)  # ZIP 文件完整路径

        # ---- 需要打包的文件关键词列表 ----
        # 文件名中包含这些关键词之一的文件将被包含在 ZIP 中
        pack_keywords = [  # 仅打包 #3-#7 和 #9-#15
            "测评调研表", "测评授权书", "风险告知书",
            "项目计划书", "测评方案",
            "首次会议记录", "测评现场记录表",
            "问题汇总", "漏洞扫描报告",
            "项目文档移交清单", "末次会议记录",
        ]

        count = 0  # 已打包文件/目录计数
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:  # 创建 ZIP（DEFLATED 压缩）
            # --- 第一步：打包匹配关键词的单文件 ---
            for fname in os.listdir(root):  # 遍历根目录
                fpath = os.path.join(root, fname)
                if not os.path.isfile(fpath) or fname == zip_name:  # 跳过目录和正在创建的 ZIP
                    continue
                name_no_ext = os.path.splitext(fname)[0]  # 取文件名（不含扩展名）
                for kw in pack_keywords:  # 遍历关键词
                    if kw in name_no_ext:  # 文件名匹配关键词
                        zf.write(fpath, fname)  # 写入 ZIP（保持原文件名）
                        count += 1  # 计数 +1
                        break  # 匹配到一个关键词即处理下一个文件

            # --- 第二步：打包渗透测试报告目录（含所有内容） ---
            for dname in os.listdir(root):
                dpath = os.path.join(root, dname)
                if os.path.isdir(dpath) and "渗透测试报告" in dname:  # 是目标目录
                    has_files = False  # 目录是否有文件（非空标志）
                    for dirpath, _, filenames in os.walk(dpath):  # 递归遍历目录
                        for fn in filenames:  # 遍历每个文件
                            fp = os.path.join(dirpath, fn)  # 文件完整路径
                            arcname = os.path.relpath(fp, root).replace("\\", "/")  # ZIP 内路径（统一斜杠）
                            zf.write(fp, arcname)  # 写入 ZIP，保持目录结构
                            count += 1
                            has_files = True  # 标记为非空
                    # 如果目录为空，添加空目录条目（保留目录结构）
                    if not has_files:
                        info = zipfile.ZipInfo(dname + "/")  # 创建目录条目（末尾 / 标记为目录）
                        zf.writestr(info, "")  # 写入空内容
                        count += 1

        # ---- 结果处理 ----
        if count > 0:  # 至少打包了一个文件
            messagebox.showinfo("打包完成",
                f"已打包 {count} 个文件\n{zip_name}")  # 显示打包结果
        else:  # 没有匹配的文件
            os.remove(zip_path)  # 删除空 ZIP 文件
            messagebox.showinfo("提示", "未找到可打包的过程文件")

    except Exception as e:  # 捕获所有异常
        messagebox.showerror("错误", f"打包失败: {e}")
