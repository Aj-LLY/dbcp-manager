"""
服务层抽象接口定义 - 依赖倒置原则 (DIP) 实现。

本模块定义服务层的抽象基类 (ABC)，上层模块（如 UI 层）应依赖这些
抽象接口而非具体实现类，从而实现依赖倒置（Dependency Inversion Principle）。

原则 #2（依赖倒置）: 高层模块不依赖低层模块，二者均依赖抽象接口。
原则 #5（技术隔离）: 业务逻辑不感知技术实现，通过抽象层封装。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from models.project import Project


# ============================================================================
# IDataService —— 数据持久化服务的抽象接口
# ============================================================================

class IDataService(ABC):
    """数据持久化服务的抽象接口。"""

    @abstractmethod
    def get_all_projects(self) -> list[dict]:
        ...

    @abstractmethod
    def get_project_by_id(self, project_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    def add_project(self, project_dict: dict) -> None:
        ...

    @abstractmethod
    def update_project(self, project_id: str, updates: dict) -> None:
        ...

    @abstractmethod
    def delete_project(self, project_id: str) -> bool:
        ...

    @abstractmethod
    def get_all_stages(self) -> list[dict]:
        ...

    @abstractmethod
    def replace_all_stages(self, stages_list: list[dict]) -> None:
        ...

    @abstractmethod
    def save(self) -> None:
        ...

    @abstractmethod
    def reload(self) -> None:
        ...


# ============================================================================
# IProjectService —— 项目管理服务的抽象接口
# ============================================================================

class IProjectService(ABC):
    """项目管理服务的抽象接口。"""

    @abstractmethod
    def get_all_projects(self) -> list["Project"]:
        ...

    @abstractmethod
    def get_project_by_id(self, project_id: str) -> Optional["Project"]:
        ...

    @abstractmethod
    def create_project(self, company_name: str, system_name: str,
                       cert_number: str, issue_date: str, level: str,
                       location: str, deadline: str, notes: str,
                       stage_id: str) -> tuple[bool, str, Optional["Project"]]:
        ...

    @abstractmethod
    def update_project(self, project_id: str,
                       company_name: Optional[str] = None,
                       system_name: Optional[str] = None,
                       cert_number: Optional[str] = None,
                       issue_date: Optional[str] = None,
                       level: Optional[str] = None,
                       location: Optional[str] = None,
                       deadline: Optional[str] = None,
                       notes: Optional[str] = None,
                       stage_id: Optional[str] = None,
                       folder_path: Optional[str] = None) -> tuple[bool, str]:
        ...

    @abstractmethod
    def delete_project(self, project_id: str) -> tuple[bool, str]:
        ...

    @abstractmethod
    def move_project(self, project_id: str,
                     new_stage_id: str) -> tuple[bool, str]:
        ...


# ============================================================================
# ILogService —— 日志追踪服务的抽象接口
# ============================================================================

class ILogService(ABC):
    """日志追踪服务的抽象接口。"""

    @abstractmethod
    def add_log(self, action: str, detail: str,
                project_id: str = "", project_name: str = "",
                from_stage: str = "", to_stage: str = "") -> None:
        ...

    @abstractmethod
    def get_all_logs(self) -> list[dict]:
        ...

    @abstractmethod
    def get_project_logs(self, project_id: str) -> list[dict]:
        ...

    @abstractmethod
    def create_log_callback(self) -> Callable[..., None]:
        ...


# ============================================================================
# IOleEmbedService —— OLE 对象嵌入服务的抽象接口（原则 #5 技术隔离）
# ============================================================================

class IOleEmbedService(ABC):
    """OLE 对象嵌入服务的抽象接口。

    封装 Excel OLE 对象插入的技术细节（win32com、openpyxl ZIP 操作等），
    业务代码不感知具体实现方式。遵循原则 #5（技术细节隔离）。
    """

    @abstractmethod
    def embed_files(self, xlsx_path: str,
                    entries: list[tuple[str, int, str]]) -> None:
        """将多个文件以 OLE 链接对象形式嵌入 XLSX 的指定单元格。

        Args:
            xlsx_path: 目标 XLSX 文件的完整路径。
            entries: [(col_letter, row_num, file_path), ...] 嵌入条目列表。

        Raises:
            OleEmbedError: 嵌入过程中发生错误。
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查 OLE 嵌入服务是否可用（如 win32com 是否已安装）。

        Returns:
            bool: True 表示服务可用。
        """
        ...


# ============================================================================
# OleEmbedError —— OLE 嵌入异常（原则 #7 显式异常）
# ============================================================================

class OleEmbedError(Exception):
    """OLE 对象嵌入过程中发生的异常。"""
    pass
