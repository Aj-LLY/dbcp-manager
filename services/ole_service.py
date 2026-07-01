"""
OLE 对象嵌入服务实现 — 原则 #5（技术隔离）。

将 win32com 依赖完全封装在本模块内，上层代码仅通过 IOleEmbedService
接口调用，不感知底层 COM 自动化细节。
"""
from __future__ import annotations

import os as _os
import logging
from typing import Optional

from services.interfaces import IOleEmbedService, OleEmbedError

_logger = logging.getLogger(__name__)


class Win32ComOleEmbedService(IOleEmbedService):
    """基于 win32com Excel COM 自动化的 OLE 嵌入实现。

    以链接方式 (Link=True) 插入 OLE 对象，双击可打开文件。
    """

    def is_available(self) -> bool:
        """检查 win32com 库是否已安装，从而判断 OLE 嵌入服务是否可用。

        Returns:
            bool: True 表示 pywin32 已安装，OLE 功能可用；False 表示未安装。
        """
        try:
            import win32com.client  # noqa: F401 — 导入检查，不实际使用
            return True  # 导入成功，服务可用
        except ImportError:
            return False  # 未安装 pywin32，服务不可用

    def embed_files(self, xlsx_path: str,
                    entries: list[tuple[str, int, str]]) -> None:
        """将多个文件以 OLE 链接对象形式嵌入 Excel 工作簿的指定单元格。

        使用 win32com Excel COM 自动化，以链接方式 (Link=True) 插入 OLE 对象，
        双击可打开源文件。处理过程中 Excel 窗口保持不可见。

        Args:
            xlsx_path: 目标 XLSX 文件的完整路径（将被打开并修改）。
            entries: 嵌入条目列表，每个元素为 (列字母, 行号, 文件路径) 元组。

        Raises:
            OleEmbedError: OLE 嵌入过程中发生任何错误时抛出。
        """
        if not entries:
            return  # 无嵌入条目，直接返回（空操作）

        _ensure_available()  # 前置检查：确保 win32com 可用

        import win32com.client  # 延迟导入，避免非 Windows 平台的导入错误

        excel: Optional[object] = None  # Excel 应用程序 COM 对象引用
        try:
            excel = win32com.client.Dispatch("Excel.Application")  # 启动 Excel COM 自动化服务
            excel.Visible = False  # 隐藏 Excel 窗口，后台执行
            excel.DisplayAlerts = False  # 禁用弹窗（如保存确认对话框）

            abs_path = _os.path.normpath(_os.path.abspath(xlsx_path))  # 规范化绝对路径
            wb = excel.Workbooks.Open(abs_path)  # 打开目标工作簿
            ws = wb.Worksheets(1)  # 获取第一个工作表

            for col_letter, row_num, fpath in entries:  # 遍历所有嵌入条目
                if not _os.path.isfile(fpath):  # 检查嵌入文件是否实际存在
                    _logger.warning("OLE 嵌入: 文件不存在 %s", fpath)  # 记录警告并跳过
                    continue  # 跳过不存在的文件，继续处理下一个条目
                try:
                    cell = ws.Range(f"{col_letter}{row_num}")  # 定位目标单元格
                    ws.OLEObjects().Add(  # 在目标单元格位置插入 OLE 链接对象
                        Filename=_os.path.abspath(fpath),  # 源文件的绝对路径
                        Link=True,  # 链接模式：双击可打开文件（非嵌入副本）
                        DisplayAsIcon=True,  # 以图标形式显示
                        Left=cell.Left,  # 对齐单元格左边界
                        Top=cell.Top,  # 对齐单元格上边界
                    )
                except Exception:
                    _logger.warning("OLE 嵌入失败: %s -> %s%s",
                                    fpath, col_letter, row_num, exc_info=True)  # 记录失败但继续

            wb.Save()  # 保存工作簿修改（写入 OLE 对象）
            wb.Close()  # 关闭工作簿
        except Exception as exc:
            raise OleEmbedError(f"OLE 嵌入过程失败: {exc}") from exc  # 包装为显式异常
        finally:
            if excel is not None:  # 确保 Excel 进程被释放
                try:
                    excel.Quit()  # 退出 Excel 应用程序
                except Exception:
                    pass  # 静默忽略退出时的异常（进程可能已终止）


def _ensure_available() -> None:
    """确保 OLE 服务可用，否则抛出明确异常（原则 #7 显式）。

    Raises:
        OleEmbedError: 当 pywin32 未安装时抛出，包含安装指导信息。
    """
    svc = Win32ComOleEmbedService()  # 创建临时实例以检查可用性
    if not svc.is_available():  # 检查 pywin32 是否已安装
        raise OleEmbedError(
            "OLE 嵌入服务不可用：请安装 pywin32（pip install pywin32）"
        )  # 抛出显式异常，提示用户安装依赖
