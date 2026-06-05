"""
批量重命名模块

提供 on_rename_click 函数：
  批量修正项目过程文件的命名，包括 ZIP 解压、文件重命名、目录重命名等。
  这是系统最核心的自动化功能之一。
"""

import os
import re
import zipfile
import shutil
from tkinter import messagebox

from models.project import Project
from ui.file_ops.folder_ops import find_project_folder


# =============================================================================
# on_rename_click - 批量重命名功能
# =============================================================================

def on_rename_click(project: Project, parent=None):
    """处理"一键重命名"按钮点击 - 批量修正项目过程文件的命名

    此方法是系统的核心自动化功能之一，执行以下流程：

    1. 查找项目文件夹（按 folder_path 或关键词搜索）
    2. 解压 ZIP 文件并重命名内容：
       - "测评方案评审记录表.zip" -> 解压提取文件
       - "测评报告评审表.zip" -> 解压提取文件（保留终审，删除初审）
    3. 删除包含"初审"的文件
    4. 修正文件命名格式为：{编号}-{公司}-{系统}-{标准名称}.{扩展名}
       - 已带编号的文件（如 "07-测评方案.docx"）：匹配关键词后更正编号和名称
       - 无编号的文件：自动添加编号和名称前缀
    5. 修正子目录命名格式：
       - "报告打印" -> "00-{公司}-{系统}-报告打印"
       - "渗透测试报告" -> "13-{公司}-{系统}-渗透测试报告"
    6. 输出操作报告（显示处理了多少文件、跳过多少文件）

    关键字映射表（key_map）：
      {匹配关键词: (编号, 标准化名称)}，按关键词长度倒序匹配避免误匹配

    Args:
        project: 项目实体对象
        parent: 父级窗口（用于消息弹窗的模态绑定）
    """
    try:
        root = find_project_folder(project)  # 查找项目文件夹路径
        if not root or not os.path.isdir(root):  # 文件夹不存在
            messagebox.showinfo("提示", "未找到项目文件夹")
            return

        # 生成文件名的前导前缀
        cname = (project.company_name or "未命名").replace("/", "_").replace("\\", "_")
        sname = (project.system_name or "").replace("/", "_").replace("\\", "_")
        new_prefix = f"{cname}-{sname}"  # 格式：公司名-系统名

        # ---- 关键字映射表 ----
        # 格式：{文件名关键词: (编号, 标准化显示名称)}
        # 按关键词长度倒序匹配，防止"测评方案评审表"误匹配为"测评方案"
        key_map = {
            "保密承诺书": ("02", "保密承诺书"),  # 02 号文件
            "测评调研表": ("03", "测评调研表"),  # 03 号文件
            "测评授权书": ("04", "测评授权书"),  # 04 号文件
            "风险告知书": ("05", "风险告知书"),  # 05 号文件
            "项目计划书": ("06", "项目计划书"),  # 06 号文件
            "测评方案": ("07", "测评方案"),  # 07 号文件（注意：需放在"测评方案评审记录表"之后匹配）
            "归档材料评审记录表": ("08", "测评方案评审表"),  # 08 号文件（历史名称）
            "测评方案评审表": ("08", "测评方案评审表"),  # 08 号文件（标准名称）
            "首次会议记录": ("09", "首次会议记录"),  # 09 号文件
            "测评现场记录表": ("10", "测评现场记录表"),  # 10 号文件
            "问题汇总": ("11", "问题汇总及整改建设书"),  # 11 号文件
            "漏洞扫描报告": ("12", "漏洞扫描报告"),  # 12 号文件
            "项目文档移交清单": ("14", "项目文档移交清单"),  # 14 号文件
            "末次会议记录": ("15", "末次会议记录"),  # 15 号文件
            "测评报告-终稿": ("16", "测评报告-终稿"),  # 16 号文件
            "测评报告评审记录表": ("17", "测评报告评审表"),  # 17 号文件（历史名称）
            "测评报告评审表": ("17", "测评报告评审表"),  # 17 号文件（标准名称）
            "服务情况评价表": ("18", "服务情况评价表"),  # 18 号文件
            "报备表": ("19", "报备表"),
            "渗透测试报告": ("13", "渗透测试报告"),  # 渗透测试报告目录
        }

        renamed = 0  # 重命名计数器（累计处理了多少个项目）
        msgs = []  # 操作报告消息列表（每步操作一条记录）

        # ========== 步骤 1: ZIP 文件解压处理 ==========
        for fname in os.listdir(root):  # 遍历项目根目录所有文件
            fpath = os.path.join(root, fname)  # 拼接文件完整路径
            if not os.path.isfile(fpath) or not fname.lower().endswith(".zip"):  # 跳过非 ZIP 文件
                continue

            # 处理"测评方案评审记录表.zip" -> 解压并重命名内容为 08
            if "测评方案评审记录表" in fname:
                try:
                    with zipfile.ZipFile(fpath, "r") as zf:  # 以读取模式打开 ZIP
                        zf.extractall(root)  # 解压全部内容到项目根目录
                    os.remove(fpath)  # 删除原 ZIP 文件
                    renamed += 1  # 计数 +1
                    msgs.append(f"解压: {fname} -> 提取文件")  # 记录操作
                except Exception as e:  # 解压失败（损坏的 ZIP、权限不足等）
                    msgs.append(f"解压失败: {fname} ({e})")

            # 处理"渗透测试报告.zip" -> 解压到独立文件夹后重命名
            if "渗透测试报告" in fname and "评审" not in fname:
                try:
                    # 解压到临时目录
                    tmp_dir = os.path.join(root, "_渗透测试报告_tmp")
                    if os.path.exists(tmp_dir):
                        shutil.rmtree(tmp_dir)
                    os.makedirs(tmp_dir)
                    with zipfile.ZipFile(fpath, "r") as zf:
                        zf.extractall(tmp_dir)
                    os.remove(fpath)
                    # 去除 ZIP 内的公共顶层目录前缀
                    items = os.listdir(tmp_dir)
                    if len(items) == 1 and os.path.isdir(os.path.join(tmp_dir, items[0])):
                        # ZIP自带一个顶层目录 -> 直接移动该目录
                        src = os.path.join(tmp_dir, items[0])
                        dst = os.path.join(root, f"13-{new_prefix}-渗透测试报告")
                    else:
                        # 文件散落 -> 创建目标目录，移入所有文件
                        dst = os.path.join(root, f"13-{new_prefix}-渗透测试报告")
                        if not os.path.exists(dst):
                            os.makedirs(dst)
                        for item in items:
                            shutil.move(os.path.join(tmp_dir, item), os.path.join(dst, item))
                        shutil.rmtree(tmp_dir)
                        renamed += 1
                        msgs.append(f"解压: {fname} -> 13-{new_prefix}-渗透测试报告/")
                        continue
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.move(src, dst)
                    shutil.rmtree(tmp_dir)
                    renamed += 1
                    msgs.append(f"解压: {fname} -> 13-{new_prefix}-渗透测试报告/")
                except Exception as e:
                    msgs.append(f"解压失败: {fname} ({e})")

            # 处理"测评报告评审表.zip" -> 解压（后续会删除初审版本）
            elif "测评报告评审表" in fname:
                try:
                    with zipfile.ZipFile(fpath, "r") as zf:  # 以读取模式打开
                        zf.extractall(root)  # 解压到项目根目录
                    os.remove(fpath)  # 删除原 ZIP
                    renamed += 1
                    msgs.append(f"解压: {fname} -> 提取文件")
                except Exception as e:
                    msgs.append(f"解压失败: {fname} ({e})")

        # ========== 步骤 2: 删除初审版本文件 ==========
        for fname in os.listdir(root):
            if "初审" in fname:  # 包含"初审"的文件（如测评报告评审表-初审.docx）
                try:
                    os.remove(os.path.join(root, fname))  # 直接删除
                    msgs.append(f"删除初审: {fname}")
                except Exception:  # 删除失败（权限等），静默跳过
                    pass

        # ========== 步骤 3: 批量重命名文件 ==========
        for fname in os.listdir(root):  # 遍历根目录所有文件
            fpath = os.path.join(root, fname)
            if not os.path.isfile(fpath) or fname.endswith(".zip"):  # 跳过 ZIP 和目录
                continue
            name_no_ext, ext = os.path.splitext(fname)  # 分离文件名和扩展名（"07-测评方案", ".docx"）

            # ---- 情况 A: 文件名已有编号前缀（如 "07-测评方案.docx"） ----
            m = re.match(r"^(\d{2})-(.+)", name_no_ext)  # 匹配 "###-内容" 格式
            if m:  # 已有编号前缀
                num = m.group(1)  # 当前编号（如 "07"）
                rest = name_no_ext[len(num) + 1:]  # 编号后面的剩余部分（如 "测评方案.docx"）
                # 按关键词长度从大到小匹配，避免"测评方案评审表"被"测评方案"先匹配
                for keyword in sorted(key_map, key=len, reverse=True):
                    if keyword in rest:  # 剩余部分中包含关键字
                        num, target_kw = key_map[keyword]  # 获取正确的编号和标准名称
                        new_name = f"{num}-{new_prefix}-{target_kw}{ext}"  # 构建标准文件名
                        if new_name != fname:  # 需要重命名
                            new_path = os.path.join(root, new_name)
                            if not os.path.exists(new_path):  # 目标文件不存在
                                os.rename(fpath, new_path)  # 执行重命名
                                renamed += 1
                            else:  # 目标文件已存在（冲突）
                                msgs.append(f"跳过(已存在): {new_name}")
                        break  # 匹配到一个关键词后退出内层循环

            # ---- 情况 B: 文件名无编号（如 "测评调研表.docx"） ----
            else:
                for keyword in sorted(key_map, key=len, reverse=True):  # 按关键词长度倒序
                    if keyword in name_no_ext:  # 文件名中包含关键字
                        num, target_kw = key_map[keyword]  # 获取编号和标准名称
                        new_name = f"{num}-{new_prefix}-{target_kw}{ext}"  # 构建标准名
                        new_path = os.path.join(root, new_name)
                        if not os.path.exists(new_path):  # 不冲突
                            os.rename(fpath, new_path)  # 重命名
                            renamed += 1
                        else:
                            msgs.append(f"跳过(已存在): {new_name}")
                        break  # 匹配到一个后退出

        # ========== 步骤 4: 子目录重命名 ==========
        for dname in os.listdir(root):  # 遍历所有目录
            dpath = os.path.join(root, dname)
            if not os.path.isdir(dpath):  # 跳过文件
                continue
            for keyword, num in {"报告打印": "00", "渗透测试报告": "13"}.items():
                if keyword in dname and (cname not in dname or sname not in dname):  # 需要更新前缀
                    new_dname = f"{num}-{new_prefix}-{keyword}"  # 标准目录名
                    new_dpath = os.path.join(root, new_dname)
                    if not os.path.exists(new_dpath):  # 不冲突
                        os.rename(dpath, new_dpath)  # 重命名目录
                        renamed += 1
                    break  # 匹配到一个关键词后退出

        # ========== 步骤 5: 显示操作报告 ==========
        if msgs:  # 有详细操作记录
            msg_text = "\n".join(msgs[:15])  # 取前 15 条
            if len(msgs) > 15:  # 超过 15 条则显示统计
                msg_text += f"\n...共 {len(msgs)} 条"
            messagebox.showinfo("操作报告", msg_text)  # 弹窗展示
        elif renamed:  # 没有详细记录但统计 > 0
            messagebox.showinfo("完成", f"已处理 {renamed} 个项目")
        else:  # 无需任何修改
            messagebox.showinfo("提示", "所有文件名已是最新，无需修改")

    except Exception as e:  # 捕获所有未预见的异常
        messagebox.showerror("错误", f"操作失败: {e}")
