"""
批量重命名模块 -- 等保测评进度管理系统

============ 本模块职责 ============
批量修正项目过程文件的命名规范，是系统最核心的自动化功能之一。
所有的等保测评项目会产生 19 类过程文件，本模块负责将其统一为：
  编号-前缀-标准名称.扩展名  的命名格式。

============ 五步处理流程 ============
  步骤 1：ZIP 文件解压处理 —— 解压特殊 ZIP 包（评审记录表、渗透测试报告等）
  步骤 2：删除初审版本文件  —— 清理文件名含"初审"的过期文件
  步骤 3：批量重命名文件    —— 按关键词映射表修正文件名
  步骤 4：子目录重命名      —— 将报告打印和渗透测试报告目录规范化
  步骤 5：显示操作报告      —— 弹窗汇总本次所有操作

============ 多系统与单系统的命名差异 ============
  多系统合并项目（all_projects 长度 > 1）：
    - 公司级文件（02/04/05/09/14/15/18/19）→ 仅含公司名前缀
      示例：02-某某公司-保密承诺书.docx
    - 系统级文件（03/06/07/08/10/11/12/13/16/17）→ 含公司-系统前缀
      示例：03-某某公司-某某系统-测评调研表.docx
    - 扫描范围：根目录（公司级）+ 各系统子目录（系统级）

  单系统项目：
    - 所有文件统一使用 公司-系统 前缀
      示例：02-某某公司-某某系统-保密承诺书.docx
    - 扫描范围：仅根目录

============ 关键词映射表说明 ============
  key_map: {关键词 → (编号, 标准名称, 是否公司级)}
  多个关键词可能映射到同一编号（如"归档材料评审记录表"和"测评方案评审表"都映射到 08）
  匹配时按关键词长度降序排列，确保长关键词优先匹配避免误判。
"""

import os        # 操作系统接口：目录遍历、路径拼接、文件重命名
import re        # 正则表达式：解析已有编号前缀（^\d{2}-）
import zipfile   # ZIP 文件处理：解压过程文件压缩包
import shutil    # 文件操作高级工具：移动和删除目录树
from tkinter import messagebox  # 消息框：显示操作报告和错误提示

from models.project import Project               # 项目实体类
from ui.file_ops.folder_ops import find_project_folder  # 查找项目文件夹


# =============================================================================
# on_rename_click - 批量重命名入口函数
# =============================================================================

def on_rename_click(project: Project, parent=None, all_projects: list = None):
    """执行批量重命名：统一修正项目过程文件为标准命名格式。

    这是系统最核心的自动化功能，按五个步骤顺序处理：
      步骤 1 — ZIP 文件解压：处理压缩包形式交付的过程文件
              - 测评方案评审记录表.zip → 解压后交由步骤 3 重命名
              - 渗透测试报告.zip → 解压到 13-{前缀}-渗透测试报告/ 目录
              - 测评报告评审表.zip → 解压（步骤 2 会清理初审版本）
      步骤 2 — 清理初审版本：删除文件名含"初审"的旧版本文件
              - 保留最终版，避免新旧版本混淆
      步骤 3 — 文件批量重命名：核心步骤，分两种情况处理
              情况 A：文件名已有编号前缀（如 "08-xxx"）
                      → 提取编号，按关键词映射修正为 编号-前缀-标准名.ext
              情况 B：文件名无编号前缀
                      → 按关键词映射直接生成 编号-前缀-标准名.ext
      步骤 4 — 子目录重命名：目录名含"报告打印"或"渗透测试报告"时
              → 修正为 00-前缀-报告打印 或 13-前缀-渗透测试报告
      步骤 5 — 弹窗报告：汇总显示本次处理的项目数和详细操作记录

    Args:
        project: 项目实体对象，提供公司名称、系统名称等元信息。
        parent: 父级 Tkinter 窗口引用（用于 messagebox 的 parent 参数）。
        all_projects: 多系统合并时所有关联项目列表，用于判断命名模式
                      和扫描范围。None 或长度 ≤ 1 时为单系统模式。

    Returns:
        None: 所有结果通过 messagebox 弹窗通知用户。

    Raises:
        不会向外抛出异常，所有异常在内部通过 messagebox.showerror 捕获并展示。
    """
    try:
        # ========== 前置：定位项目文件夹并准备变量 ==========
        root = find_project_folder(project)
        if not root or not os.path.isdir(root):
            messagebox.showinfo("提示", "未找到项目文件夹")
            return

        # 清理路径非法字符（/ 和 \\ 替换为 _）
        cname = (project.company_name or "未命名").replace("/", "_").replace("\\", "_")
        sname = (project.system_name or "").replace("/", "_").replace("\\", "_")
        is_multi = all_projects and len(all_projects) > 1

        # 构建两种前缀（多系统模式下的选择策略见 _get_prefix）
        # company_prefix：仅含公司名，用于多系统共享的公司级文件
        company_prefix = cname
        # system_prefix：含公司-系统，用于系统专属文件（及单系统模式的所有文件）
        system_prefix = f"{cname}-{sname}"

        # 公司级文件关键词集合 —— 这些文件在多系统合并时使用公司名前缀
        # 编号对应：02=保密承诺书, 04=测评授权书, 05=风险告知书, 09=首次会议记录
        #          14=项目文档移交清单, 15=末次会议记录, 18=服务情况评价表, 19=报备表
        company_keys = {"保密承诺书", "测评授权书", "风险告知书", "首次会议记录",
                        "项目文档移交清单", "末次会议记录", "服务情况评价表", "报备表"}

        # ---- 构建关键词→标准信息映射表 ----
        # 结构: {关键词字符串: (文件编号, 标准名称, 是否公司级)}
        # 一个标准名称可能有多个关键词别名（如 "归档材料评审记录表" 和 "测评方案评审表"
        # 都对应 08-测评方案评审表）
        key_map = {}
        for kw, (num, name) in [
            ("保密承诺书", ("02", "保密承诺书")),                   # 公司级文件
            ("测评调研表", ("03", "测评调研表")),                   # 系统级文件
            ("测评授权书", ("04", "测评授权书")),                   # 公司级文件
            ("风险告知书", ("05", "风险告知书")),                   # 公司级文件
            ("项目计划书", ("06", "项目计划书")),                   # 系统级文件
            ("测评方案", ("07", "测评方案")),                       # 系统级文件
            ("归档材料评审记录表", ("08", "测评方案评审表")),       # 别名 → 08
            ("测评方案评审表", ("08", "测评方案评审表")),           # 标准名 → 08
            ("首次会议记录", ("09", "首次会议记录")),               # 公司级文件
            ("测评现场记录表", ("10", "测评现场记录表")),           # 系统级文件
            ("问题汇总", ("11", "问题汇总及整改建设书")),           # 系统级文件
            ("漏洞扫描报告", ("12", "漏洞扫描报告")),               # 系统级文件
            ("项目文档移交清单", ("14", "项目文档移交清单")),       # 公司级文件
            ("末次会议记录", ("15", "末次会议记录")),               # 公司级文件
            ("测评报告-终稿", ("16", "测评报告-终稿")),             # 系统级文件
            ("测评报告评审记录表", ("17", "测评报告评审表")),       # 别名 → 17
            ("测评报告评审表", ("17", "测评报告评审表")),           # 标准名 → 17
            ("服务情况评价表", ("18", "服务情况评价表")),           # 公司级文件
            ("报备表", ("19", "报备表")),                           # 公司级文件
            ("渗透测试报告", ("13", "渗透测试报告")),               # 系统级文件
        ]:
            is_company = kw in company_keys  # 判断是否属于公司级
            key_map[kw] = (num, name, is_company)

        # ========== 内部辅助函数 ==========

        def _sys_prefix_for(scan_root):
            """根据扫描目录名推断对应的系统级前缀。

            在多系统模式下，各系统子目录（如"某某系统A"）中的文件
            需要使用该子目录对应系统的前缀。此函数将子目录名与
            all_projects 中各项目的系统名进行双向模糊匹配。

            Args:
                scan_root: 当前扫描的目录绝对路径。

            Returns:
                str: 匹配到的系统级前缀（格式：公司-系统名），
                     无法匹配时回退到默认 system_prefix。
            """
            if scan_root == root:
                # 根目录使用默认系统前缀
                return system_prefix
            # 提取目录名（不含路径）
            dname = os.path.basename(scan_root)
            # 遍历所有关联项目，尝试将系统名与目录名匹配
            for p in (all_projects or []):
                sn = (p.system_name or "").replace("/", "_").replace("\\", "_")
                if sn and (sn in dname or dname in sn):
                    return f"{cname}-{sn}"  # 匹配成功：使用对应系统的前缀
            return system_prefix  # 无匹配：回退到默认

        def _get_prefix(is_company_lvl, scan_root=root):
            """根据文件级别和扫描位置返回正确的前缀。

            前缀选择规则（按优先级）：
              1. 多系统 + 公司级文件 → company_prefix（仅公司名）
              2. 多系统 + 非根目录扫描 → _sys_prefix_for(scan_root)（子系统前缀）
              3. 其他情况 → system_prefix（公司-系统）

            Args:
                is_company_lvl: 该文件是否为公司级（True=公司级，False=系统级）。
                scan_root: 当前扫描目录路径。

            Returns:
                str: 该文件应使用的前缀字符串。
            """
            if is_multi and is_company_lvl:
                # 多系统模式下公司级文件共享，只用公司名
                return company_prefix
            if is_multi and scan_root != root:
                # 多系统模式下子系统目录内的文件，使用子系统前缀
                return _sys_prefix_for(scan_root)
            # 默认：公司-系统前缀（单系统模式或根目录系统级文件）
            return system_prefix

        # 操作统计计数器
        renamed = 0   # 累计重命名/解压/移动的项目数
        msgs = []     # 操作详情消息列表（每条一行）

        # ---- 构建扫描目录列表 ----
        # 单系统项目：仅扫描根目录
        # 多系统合并：扫描根目录（公司级文件）+ 各系统子目录（系统级文件）
        # 排除规则：跳过"报告打印"目录和"01-其他归档文件"目录
        scan_dirs = [root]
        if is_multi:
            for dname in os.listdir(root):
                dpath = os.path.join(root, dname)
                if os.path.isdir(dpath) and "报告打印" not in dname \
                        and dname != "01-其他归档文件":
                    scan_dirs.append(dpath)

        # ==================================================================
        # 步骤 1：ZIP 文件解压处理
        # ==================================================================
        # 处理三种特殊 ZIP 包：
        #   ① 测评方案评审记录表.zip → 直接解压到当前目录（后续步骤 3 会重命名）
        #   ② 渗透测试报告.zip → 解压到临时目录，移入 13-前缀-渗透测试报告/
        #   ③ 测评报告评审表.zip → 解压到当前目录（步骤 2 会清理初审版本）
        for scan_root in scan_dirs:
            for fname in os.listdir(scan_root):
                fpath = os.path.join(scan_root, fname)
                # 仅处理文件类型的 ZIP
                if not os.path.isfile(fpath) or not fname.lower().endswith(".zip"):
                    continue

                extract_dst = scan_root  # 默认解压目标与 ZIP 同目录

                # --- ① 测评方案评审记录表.zip ---
                # 解压后的内容可能是编号不规范的评审表文件，交由步骤 3 统一重命名为 08
                if "测评方案评审记录表" in fname:
                    try:
                        with zipfile.ZipFile(fpath, "r") as zf:
                            zf.extractall(extract_dst)  # 解压全部内容
                        os.remove(fpath)                 # 删除原始 ZIP
                        renamed += 1
                        msgs.append(f"解压: {fname} -> 提取文件")
                    except Exception as e:
                        msgs.append(f"解压失败: {fname} ({e})")

                # --- ② 渗透测试报告.zip（排除评审相关的 ZIP） ---
                # 解压逻辑较复杂，因为 ZIP 结构不确定：
                #   - 如果解压后只有 1 个子目录 → 该目录即渗透测试报告内容
                #   - 如果解压后是多个散文件 → 创建新目录统一收纳
                if "渗透测试报告" in fname and "评审" not in fname:
                    try:
                        # 创建临时解压目录（命名为 _渗透测试报告_tmp 避免冲突）
                        tmp_dir = os.path.join(scan_root, "_渗透测试报告_tmp")
                        if os.path.exists(tmp_dir):
                            shutil.rmtree(tmp_dir)  # 清理可能残留的旧临时目录
                        os.makedirs(tmp_dir)
                        with zipfile.ZipFile(fpath, "r") as zf:
                            zf.extractall(tmp_dir)  # 解压到临时目录
                        os.remove(fpath)            # 删除原始 ZIP

                        items = os.listdir(tmp_dir)  # 临时目录内容
                        dst = os.path.join(scan_root,
                                          f"13-{_sys_prefix_for(scan_root)}-渗透测试报告")

                        if len(items) == 1 and os.path.isdir(os.path.join(tmp_dir, items[0])):
                            # 仅 1 个子目录：直接将该子目录作为最终目录
                            src = os.path.join(tmp_dir, items[0])
                            if os.path.exists(dst):
                                shutil.rmtree(dst)  # 覆盖已存在的目录
                            shutil.move(src, dst)
                        else:
                            # 多个文件或混合内容：创建目标目录后批量移入
                            if not os.path.exists(dst):
                                os.makedirs(dst)
                            for item in items:
                                shutil.move(os.path.join(tmp_dir, item),
                                           os.path.join(dst, item))
                        # 清理临时目录
                        shutil.rmtree(tmp_dir)
                        renamed += 1
                        msgs.append(
                            f"解压: {fname} -> 13-{_sys_prefix_for(scan_root)}-渗透测试报告/")
                    except Exception as e:
                        msgs.append(f"解压失败: {fname} ({e})")

                # --- ③ 测评报告评审表.zip ---
                # 直接解压，解压出的文件可能包含"初审"版本，由步骤 2 统一清理
                elif "测评报告评审表" in fname:
                    try:
                        with zipfile.ZipFile(fpath, "r") as zf:
                            zf.extractall(extract_dst)
                        os.remove(fpath)
                        renamed += 1
                        msgs.append(f"解压: {fname} -> 提取文件")
                    except Exception as e:
                        msgs.append(f"解压失败: {fname} ({e})")

        # ==================================================================
        # 步骤 2：删除初审版本文件
        # ==================================================================
        # 遍历所有扫描目录，删除文件名中包含"初审"的文件
        # 保留的将是最终版本（如 "17-测评报告评审表.docx"），
        # 删除的是草稿版本（如 "17-测评报告评审表(初审).docx"）
        for scan_root in scan_dirs:
            for fname in os.listdir(scan_root):
                if "初审" in fname:
                    try:
                        os.remove(os.path.join(scan_root, fname))
                        msgs.append(f"删除初审: {fname}")
                    except Exception:
                        pass  # 删除失败不阻塞（可能文件已不存在或被锁定）

        # ==================================================================
        # 步骤 3：批量重命名文件（核心步骤）
        # ==================================================================
        # 遍历所有扫描目录中的每个文件，按两种情况处理：
        for scan_root in scan_dirs:
            for fname in os.listdir(scan_root):
                fpath = os.path.join(scan_root, fname)
                # 跳过目录和 ZIP 文件（ZIP 已在步骤 1 处理）
                if not os.path.isfile(fpath) or fname.endswith(".zip"):
                    continue
                # 分离文件名和扩展名
                name_no_ext, ext = os.path.splitext(fname)

                # ---- 情况 A：文件名已有编号前缀（如 "08-测评方案评审表.docx"） ----
                # 正则匹配：2 位数字开头 + 连字符
                m = re.match(r"^(\d{2})-(.+)", name_no_ext)
                if m:
                    num = m.group(1)          # 提取编号（如 "08"）
                    rest = name_no_ext[len(num) + 1:]  # 编号后面的部分（如 "测评方案评审表"）
                    # 按关键词长度降序遍历，确保长关键词优先匹配
                    # 例：rest="测评方案评审记录表"时，先匹配"测评方案评审记录表"而非"测评方案"
                    for keyword in sorted(key_map, key=len, reverse=True):
                        if keyword in rest:
                            num, target_kw, is_co = key_map[keyword]
                            pfx = _get_prefix(is_co, scan_root)  # 获取正确前缀
                            new_name = f"{num}-{pfx}-{target_kw}{ext}"
                            if new_name != fname:
                                new_path = os.path.join(scan_root, new_name)
                                if not os.path.exists(new_path):
                                    os.rename(fpath, new_path)
                                    renamed += 1
                                    msgs.append(f"✓ {fname} → {new_name}")
                                else:
                                    msgs.append(f"跳过(已存在): {new_name}")
                            break

                # ---- 情况 B：文件名无编号前缀 ----
                else:
                    for keyword in sorted(key_map, key=len, reverse=True):
                        if keyword in name_no_ext:
                            num, target_kw, is_co = key_map[keyword]
                            pfx = _get_prefix(is_co, scan_root)
                            new_name = f"{num}-{pfx}-{target_kw}{ext}"
                            new_path = os.path.join(scan_root, new_name)
                            if not os.path.exists(new_path):
                                os.rename(fpath, new_path)
                                renamed += 1
                                msgs.append(f"✓ {fname} → {new_name}")
                            else:
                                msgs.append(f"跳过(已存在): {new_name}")
                            break

        # ==================================================================
        # 步骤 4：子目录重命名
        # ==================================================================
        # 处理两种目录：
        #   ① "报告打印"目录 → 00-前缀-报告打印（公司级，编号 00）
        #   ② "渗透测试报告"目录 → 13-前缀-渗透测试报告（系统级，编号 13）
        # 重命名条件：目录名含关键词 且 当前未包含正确的公司/系统名前缀
        for scan_root in scan_dirs:
            for dname in os.listdir(scan_root):
                dpath = os.path.join(scan_root, dname)
                if not os.path.isdir(dpath):
                    continue  # 跳过文件
                for keyword, num, is_co in [("报告打印", "00", True),
                                             ("渗透测试报告", "13", False)]:
                    pfx = _get_prefix(is_co, scan_root)
                    # 仅当目录名含关键词且未含正确前缀时才重命名
                    if keyword in dname and (cname not in dname or
                                             (sname and sname not in dname)):
                        new_dname = f"{num}-{pfx}-{keyword}"
                        new_dpath = os.path.join(scan_root, new_dname)
                        if not os.path.exists(new_dpath):
                            os.rename(dpath, new_dpath)
                            renamed += 1
                        break  # 一个目录只匹配一次

        # ==================================================================
        # 步骤 5：显示操作报告
        # ==================================================================
        # 分类统计
        renames = [m for m in msgs if m.startswith("✓")]
        skips = [m for m in msgs if m.startswith("跳过")]
        others = [m for m in msgs if not m.startswith("✓") and not m.startswith("跳过")]

        lines = []
        if renames:
            lines.append(f"--- 重命名成功 ({len(renames)}个) ---")
            lines.extend(renames[:20])
            if len(renames) > 20:
                lines.append(f"...还有 {len(renames)-20} 个")
        if skips:
            if lines: lines.append("")
            lines.append(f"--- 跳过 ({len(skips)}个) ---")
            lines.extend(skips[:5])
            if len(skips) > 5:
                lines.append(f"...还有 {len(skips)-5} 个")
        if others:
            if lines: lines.append("")
            lines.append(f"--- 其他操作 ({len(others)}个) ---")
            lines.extend(others[:5])
            if len(others) > 5:
                lines.append(f"...还有 {len(others)-5} 个")

        if lines:
            messagebox.showinfo("操作报告", "\n".join(lines))
        elif renamed:
            messagebox.showinfo("完成", f"已处理 {renamed} 个项目")
        else:
            messagebox.showinfo("提示", "所有文件名已是最新，无需修改")

    except Exception as e:
        # 顶层异常兜底（如权限不足、磁盘满等系统级错误）
        messagebox.showerror("错误", f"操作失败: {e}")
