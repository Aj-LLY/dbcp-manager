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

def on_rename_click(project: Project, parent=None, all_projects: list = None):
    """批量重命名项目过程文件。

    多系统: 公司级文件(02/04/05/09/14/15/18/19)→公司名前缀,
           系统级文件(03/06/07/08/10/11/12/13/16/17)→公司-系统前缀

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

        # 前缀: 多系统时公司级文件只用公司名, 系统级文件用公司-系统
        company_prefix = cname
        system_prefix = f"{cname}-{sname}"

        # 公司级文件关键词（多系统时共享）: 02,04,05,09,14,15,18,19
        company_keys = {"保密承诺书", "测评授权书", "风险告知书", "首次会议记录",
                        "项目文档移交清单", "末次会议记录", "服务情况评价表", "报备表"}

        # ---- 关键字映射表 (关键词: (编号, 标准名, 是否公司级)) ----
        key_map = {}
        for kw, (num, name) in [
            ("保密承诺书", ("02", "保密承诺书")),
            ("测评调研表", ("03", "测评调研表")),
            ("测评授权书", ("04", "测评授权书")),
            ("风险告知书", ("05", "风险告知书")),
            ("项目计划书", ("06", "项目计划书")),
            ("测评方案", ("07", "测评方案")),
            ("归档材料评审记录表", ("08", "测评方案评审表")),
            ("测评方案评审表", ("08", "测评方案评审表")),
            ("首次会议记录", ("09", "首次会议记录")),
            ("测评现场记录表", ("10", "测评现场记录表")),
            ("问题汇总", ("11", "问题汇总及整改建设书")),
            ("漏洞扫描报告", ("12", "漏洞扫描报告")),
            ("项目文档移交清单", ("14", "项目文档移交清单")),
            ("末次会议记录", ("15", "末次会议记录")),
            ("测评报告-终稿", ("16", "测评报告-终稿")),
            ("测评报告评审记录表", ("17", "测评报告评审表")),
            ("测评报告评审表", ("17", "测评报告评审表")),
            ("服务情况评价表", ("18", "服务情况评价表")),
            ("报备表", ("19", "报备表")),
            ("渗透测试报告", ("13", "渗透测试报告")),
        ]:
            is_company = kw in company_keys
            key_map[kw] = (num, name, is_company)

        def _get_prefix(is_company_lvl):
            if is_multi and is_company_lvl:
                return company_prefix
            return system_prefix

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
                        dst = os.path.join(root, f"13-{system_prefix}-渗透测试报告")
                    else:
                        dst = os.path.join(root, f"13-{system_prefix}-渗透测试报告")
                        if not os.path.exists(dst):
                            os.makedirs(dst)
                        for item in items:
                            shutil.move(os.path.join(tmp_dir, item), os.path.join(dst, item))
                        shutil.rmtree(tmp_dir)
                        renamed += 1
                        msgs.append(f"解压: {fname} -> 13-{system_prefix}-渗透测试报告/")
                        continue
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.move(src, dst)
                    shutil.rmtree(tmp_dir)
                    renamed += 1
                    msgs.append(f"解压: {fname} -> 13-{system_prefix}-渗透测试报告/")
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
                    if keyword in rest:
                        num, target_kw, is_co = key_map[keyword]
                        pfx = _get_prefix(is_co)
                        new_name = f"{num}-{pfx}-{target_kw}{ext}"
                        if new_name != fname:
                            new_path = os.path.join(root, new_name)
                            if not os.path.exists(new_path):
                                os.rename(fpath, new_path)
                                renamed += 1
                            else:
                                msgs.append(f"跳过(已存在): {new_name}")
                        break

            # ---- 情况 B: 文件名无编号 ----
            else:
                for keyword in sorted(key_map, key=len, reverse=True):
                    if keyword in name_no_ext:
                        num, target_kw, is_co = key_map[keyword]
                        pfx = _get_prefix(is_co)
                        new_name = f"{num}-{pfx}-{target_kw}{ext}"
                        new_path = os.path.join(root, new_name)
                        if not os.path.exists(new_path):
                            os.rename(fpath, new_path)
                            renamed += 1
                        else:
                            msgs.append(f"跳过(已存在): {new_name}")
                        break

        # ========== 步骤 4: 子目录重命名 ==========
        for dname in os.listdir(root):  # 遍历所有目录
            dpath = os.path.join(root, dname)
            if not os.path.isdir(dpath):  # 跳过文件
                continue
            for keyword, num, is_co in [("报告打印", "00", True), ("渗透测试报告", "13", False)]:
                pfx = _get_prefix(is_co)
                if keyword in dname and (cname not in dname or (sname and sname not in dname)):
                    new_dname = f"{num}-{pfx}-{keyword}"
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
