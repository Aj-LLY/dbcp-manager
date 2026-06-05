"""
ui.file_ops package -- 项目文件操作子模块集合

从 ui.card_file_ops 拆分出的独立模块：
  - folder_ops:  项目文件夹查找与打开
  - init_project: 项目初始化（创建子目录和模板）
  - rename:       批量重命名过程文件
  - zip_pack:     过程文档 ZIP 打包
  - card_file_ops 保留: on_report_print_click（报告打印）
"""

from ui.file_ops.folder_ops import find_project_folder, on_folder_click
from ui.file_ops.init_project import on_init_click
from ui.file_ops.rename import on_rename_click
from ui.file_ops.zip_pack import on_zip_click

__all__ = [
    "find_project_folder",
    "on_folder_click",
    "on_init_click",
    "on_rename_click",
    "on_zip_click",
]
