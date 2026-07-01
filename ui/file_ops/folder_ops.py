"""
项目文件夹查找与打开模块

提供两个独立函数：
  - find_project_folder(project) -> str: 查找项目文件夹路径
  - on_folder_click(project): 在系统文件管理器中打开项目文件夹
"""

import os
import sys
import subprocess

from models.project import Project
from utils.config import Config


# =============================================================================
# find_project_folder - 查找项目文件夹路径
# =============================================================================

def find_project_folder(project: Project) -> str:
    """根据项目信息查找本地文件夹路径

    查找策略（按优先级从高到低）：
      1. 项目存储的 folder_path 属性（最直接，优先使用）
      2. 按公司名 + 系统名 + 创建日期的关键词模糊搜索（兜底方案）

    搜索关键词：
      - 公司名称（清理路径非法字符后）
      - 系统名称（清理路径非法字符后）
      - 创建日期（YYMMDD 格式，取项目 created_at 前 10 位的后 6 位）

    Args:
        project: 项目实体对象

    Returns:
        str: 找到的文件夹路径，未找到返回空字符串 ""
    """
    # 策略 1：优先使用项目存储的文件夹路径
    if project.folder_path and os.path.isdir(project.folder_path):
        return project.folder_path  # 直接返回存储的路径

    # 策略 2：按关键词搜索（兜底方案）
    base = Config.get_data_dir()  # 获取程序数据根目录
    if not os.path.exists(base):  # 根目录不存在则无法搜索
        return ""  # 无数据目录，返回空
    # 清理名称中的路径非法字符（/ 和 \\ 在 Windows/Mac 路径中无效），统一替换为下划线
    cname = (project.company_name or "未命名").replace("/", "_").replace("\\", "_")
    sname = (project.system_name or "").replace("/", "_").replace("\\", "_")
    date_str = ""  # 日期关键词（默认为空，不参与过滤）
    if project.created_at:  # 有创建时间则提取日期部分
        # YYYY-MM-DD 去掉连字符后取后 6 位 -> YYMMDD
        date_str = project.created_at[:10].replace("-", "")[2:]

    # 遍历数据目录，查找匹配的文件夹名
    for name in os.listdir(base):
        full = os.path.join(base, name)  # 拼接完整路径
        if not os.path.isdir(full):  # 非目录跳过
            continue
        # 匹配规则：名称中同时包含公司名、系统名（可选）、日期（可选）
        if cname in name and (not sname or sname in name) and (not date_str or date_str in name):
            return full  # 找到匹配，返回路径
    return ""  # 未找到任何匹配


# =============================================================================
# on_folder_click - 打开项目文件夹
# =============================================================================

def on_folder_click(project: Project):
    """处理"打开文件夹"按钮点击 - 在系统文件管理器中打开项目目录

    调用各操作系统的默认文件管理器：
      - Windows：os.startfile(path) 直接打开（等效于在资源管理器中双击该文件夹）
      - Linux/macOS：subprocess.run(["xdg-open", path]) 调用桌面环境默认管理器

    查找失败或打开失败时静默处理，不弹出错误提示，避免打断用户工作流。

    Args:
        project: 项目实体对象
    """
    try:
        path = find_project_folder(project)  # 查找项目文件夹路径
        if path and os.path.isdir(path):  # 路径存在且确实是一个目录
            if sys.platform == "win32":  # Windows 系统
                os.startfile(path)  # 使用 Windows 默认方式打开（类似双击文件夹效果）
            else:  # 非 Windows 系统（Linux/macOS）
                subprocess.run(["xdg-open", path])  # 调用 xdg-open 命令行工具打开
    except Exception:  # 打开失败（权限不足、路径不存在、系统限制等）
        pass  # 静默处理：打开失败不阻塞主流程
