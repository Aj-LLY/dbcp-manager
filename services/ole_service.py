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
        try:
            import win32com.client  # noqa: F401
            return True
        except ImportError:
            return False

    def embed_files(self, xlsx_path: str,
                    entries: list[tuple[str, int, str]]) -> None:
        if not entries:
            return

        _ensure_available()

        import win32com.client

        excel: Optional[object] = None
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False

            abs_path = _os.path.normpath(_os.path.abspath(xlsx_path))
            wb = excel.Workbooks.Open(abs_path)
            ws = wb.Worksheets(1)

            for col_letter, row_num, fpath in entries:
                if not _os.path.isfile(fpath):
                    _logger.warning("OLE 嵌入: 文件不存在 %s", fpath)
                    continue
                try:
                    cell = ws.Range(f"{col_letter}{row_num}")
                    ws.OLEObjects().Add(
                        Filename=_os.path.abspath(fpath),
                        Link=True,
                        DisplayAsIcon=True,
                        Left=cell.Left,
                        Top=cell.Top,
                    )
                except Exception:
                    _logger.warning("OLE 嵌入失败: %s -> %s%s",
                                    fpath, col_letter, row_num, exc_info=True)

            wb.Save()
            wb.Close()
        except Exception as exc:
            raise OleEmbedError(f"OLE 嵌入过程失败: {exc}") from exc
        finally:
            if excel is not None:
                try:
                    excel.Quit()
                except Exception:
                    pass


def _ensure_available() -> None:
    """确保 OLE 服务可用，否则抛出明确异常（原则 #7 显式）。"""
    svc = Win32ComOleEmbedService()
    if not svc.is_available():
        raise OleEmbedError(
            "OLE 嵌入服务不可用：请安装 pywin32（pip install pywin32）"
        )
