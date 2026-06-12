"""
过程文档 ZIP 打包模块 -- 等保测评进度管理系统

============ 本模块职责 ============
将项目的过程文件按预定义的关键词集筛选后，压缩为一个统一的 ZIP 归档文件，
方便向客户交付或存档。

============ 打包内容 ============
包含以下两类内容：
  1. 单文件（11 类关键词匹配）：
     - 测评调研表、测评授权书、风险告知书
     - 项目计划书、测评方案
     - 首次会议记录、测评现场记录表
     - 问题汇总、漏洞扫描报告
     - 项目文档移交清单、末次会议记录
  2. 整目录：
     - 渗透测试报告/ 目录及其所有子文件和子目录

============ 不打包的内容 ============
  - 报告打印目录（00-前缀）
  - 01-其他归档文件目录
  - ZIP 文件自身（避免无限递归）
  - 保密承诺书（编号 02，属内部文件）
  - 服务情况评价表（编号 18，属内部文件）
  - 报备表（编号 19，属内部文件）

============ 多系统模式 ============
多系统合并时，扫描根目录（公司级文件）+ 各系统子目录，
所有文件的 ZIP 内部路径保持相对于根目录的层级结构。
ZIP 文件名：{公司名}-过程文档.zip（不含系统名，因为包含所有子系统）。
"""

import os         # 操作系统接口：目录遍历、路径拼接、文件删除
import zipfile    # ZIP 压缩：创建压缩归档文件，使用 DEFLATED 压缩算法
from tkinter import messagebox  # 消息框：通知用户打包结果

from models.project import Project               # 项目实体类
from ui.file_ops.folder_ops import find_project_folder  # 查找项目文件夹


# =============================================================================
# on_zip_click - 打包过程文档入口函数
# =============================================================================

def on_zip_click(project: Project, parent=None, all_projects: list = None):
    """处理"打包过程文档"按钮点击：筛选并压缩项目过程文件为 ZIP 归档。

    打包流程（3 步）：
      步骤 1 — 打包单文件：遍历扫描目录，将文件名匹配 pack_keywords 的
              文件按相对路径写入 ZIP（保持目录结构）。
      步骤 2 — 打包渗透测试报告目录：将整个渗透测试报告目录树递归写入 ZIP，
              包括所有子文件和子目录。空目录也保留（创建目录条目）。
      步骤 3 — 报告结果：有文件时弹窗显示打包数量和文件名；
              无文件时删除空 ZIP 并提示。

    ZIP 配置：
      - 压缩算法：ZIP_DEFLATED（标准 Deflate 算法，兼容性最好）
      - 文件路径：使用正斜杠 "/" 分隔（跨平台兼容）
      - 相对路径：arcname 基于项目根目录的相对路径

    Args:
        project: 项目实体对象。
        parent: 父级 Tkinter 窗口引用（用于 messagebox 的 parent 参数）。
        all_projects: 多系统合并时所有关联项目列表，用于判断扫描范围。

    Returns:
        None: 结果通过 messagebox 弹窗展示。
    """
    try:
        # ========== 前置：定位项目文件夹 ==========
        root = find_project_folder(project)
        if not root or not os.path.isdir(root):
            messagebox.showinfo("提示", "未找到项目文件夹")
            return

        # 清理路径非法字符
        cname = (project.company_name or "未命名").replace("/", "_").replace("\\", "_")
        sname = (project.system_name or "").replace("/", "_").replace("\\", "_")
        is_multi = all_projects and len(all_projects) > 1

        # 单系统：{公司}-{系统}-过程文档.zip
        # 多系统：{公司}-过程文档.zip（包含所有子系统的文件）
        zip_name = f"{cname}-{sname}-过程文档.zip" if not is_multi else f"{cname}-过程文档.zip"
        zip_path = os.path.join(root, zip_name)

        # ---- 构建扫描目录列表 ----
        # 单系统：仅根目录
        # 多系统：根目录 + 各系统子目录（排除报告打印和归档目录）
        scan_dirs = [root]
        if is_multi:
            for dname in os.listdir(root):
                dpath = os.path.join(root, dname)
                if os.path.isdir(dpath) and "报告打印" not in dname \
                        and dname != "01-其他归档文件":
                    scan_dirs.append(dpath)

        # ---- 定义打包关键词列表 ----
        # 这些关键词对应等保测评过程中需要交付给客户的文件类型
        # 注意：不包括保密承诺书(02)、服务情况评价表(18)、报备表(19)等内部文件
        pack_keywords = [
            "测评调研表",        # 03-系统信息安全调研记录
            "测评授权书",        # 04-测评授权与委托书
            "风险告知书",        # 05-测评风险告知书
            "项目计划书",        # 06-测评项目计划书
            "测评方案",          # 07-安全测评技术方案
            "首次会议记录",      # 09-项目启动会议纪要
            "测评现场记录表",    # 10-现场测评工作记录
            "问题汇总",          # 11-问题汇总及整改建议书
            "漏洞扫描报告",      # 12-系统漏洞扫描分析报告
            "项目文档移交清单",  # 14-项目成果文档移交清单
            "末次会议记录",      # 15-项目总结会议纪要
        ]

        count = 0  # 已打包文件计数器

        # 创建 ZIP 文件（使用 DEFLATED 压缩算法，平衡压缩率和速度）
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # ========== 步骤 1：打包匹配关键词的单文件 ==========
            for scan_root in scan_dirs:
                for fname in os.listdir(scan_root):
                    fpath = os.path.join(scan_root, fname)
                    # 跳过目录、跳过打包生成的 ZIP 自身（避免循环打包）
                    if not os.path.isfile(fpath) or fname == zip_name:
                        continue
                    # 用无扩展名的文件名进行关键词匹配
                    name_no_ext = os.path.splitext(fname)[0]
                    for kw in pack_keywords:
                        if kw in name_no_ext:  # 关键词在文件名中
                            # 计算相对于项目根目录的路径（ZIP 内部路径统一使用 / 分隔）
                            arcname = os.path.relpath(fpath, root).replace("\\", "/")
                            zf.write(fpath, arcname)  # 写入 ZIP
                            count += 1
                            break  # 一个文件只匹配一次

            # ========== 步骤 2：打包渗透测试报告目录（递归） ==========
            # 渗透测试报告是一个目录（13-前缀-渗透测试报告），而非单文件
            # 使用 os.walk 递归遍历目录树，将所有子文件和子目录写入 ZIP
            for scan_root in scan_dirs:
                for dname in os.listdir(scan_root):
                    dpath = os.path.join(scan_root, dname)
                    if os.path.isdir(dpath) and "渗透测试报告" in dname:
                        has_files = False  # 标记目录中是否有实际文件
                        # 递归遍历目录树（os.walk 自动处理子目录）
                        for dirpath, _, filenames in os.walk(dpath):
                            for fn in filenames:
                                fp = os.path.join(dirpath, fn)
                                arcname = os.path.relpath(fp, root).replace("\\", "/")
                                zf.write(fp, arcname)  # 写入文件
                                count += 1
                                has_files = True
                        # 空目录处理：ZIP 格式支持仅目录条目（无内容）
                        # 在客户解压时确保目录结构完整（即使目录为空）
                        if not has_files:
                            arcname = os.path.relpath(dpath, root).replace("\\", "/") + "/"
                            info = zipfile.ZipInfo(arcname)  # 创建目录条目
                            zf.writestr(info, "")            # 写入空内容
                            count += 1

        # ========== 步骤 3：报告打包结果 ==========
        if count > 0:
            # 打包成功：显示文件数量和 ZIP 文件名
            messagebox.showinfo("打包完成",
                f"已打包 {count} 个文件\n{zip_name}")
        else:
            # 无匹配文件：删除空 ZIP，并提示用户
            os.remove(zip_path)  # 清理无用的空 ZIP 文件
            messagebox.showinfo("提示", "未找到可打包的过程文件")

    except Exception as e:
        # 顶层异常：权限不足、磁盘满、文件被占用等
        messagebox.showerror("错误", f"打包失败: {e}")
