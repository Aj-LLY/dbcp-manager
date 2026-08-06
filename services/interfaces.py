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
    """数据持久化服务的抽象接口。

    定义系统数据层的统一访问契约，所有具体实现（如 DataService）
    必须实现本接口中定义的全部方法。
    """

    @abstractmethod
    def get_all_projects(self) -> list[dict]:
        """获取所有项目的字典列表。

        Returns:
            list[dict]: 项目字典列表，每个元素包含项目的完整字段。
        """
        ...

    @abstractmethod
    def get_project_by_id(self, project_id: str) -> Optional[dict]:
        """根据项目ID查找单个项目。

        Args:
            project_id: 要查找的项目唯一标识符。

        Returns:
            dict | None: 匹配的项目字典，未找到时返回 None。
        """
        ...

    @abstractmethod
    def add_project(self, project_dict: dict) -> None:
        """向数据中添加新项目。

        Args:
            project_dict: 新项目的完整字段字典。
        """
        ...

    @abstractmethod
    def update_project(self, project_id: str, updates: dict) -> None:
        """更新指定项目的字段。

        Args:
            project_id: 要更新的项目唯一标识符。
            updates: 需要更新的字段字典（键为字段名，值为新内容）。
        """
        ...

    @abstractmethod
    def delete_project(self, project_id: str) -> bool:
        """删除指定项目。

        Args:
            project_id: 要删除的项目唯一标识符。

        Returns:
            bool: True 表示删除成功，False 表示项目不存在。
        """
        ...

    @abstractmethod
    def get_all_stages(self) -> list[dict]:
        """获取所有流程阶段的字典列表，按 order 升序排列。

        Returns:
            list[dict]: 按 order 字段升序排列的阶段字典列表。
        """
        ...

    @abstractmethod
    def replace_all_stages(self, stages_list: list[dict]) -> None:
        """替换全部流程阶段（批量更新操作）。

        Args:
            stages_list: 新的阶段字典列表，完全替换现有的 workflow_stages。
        """
        ...

    @abstractmethod
    def add_stage(self, stage_dict: dict) -> None:
        """添加一个新的流程阶段到数据中。

        Args:
            stage_dict: 阶段完整字段字典。
        """
        ...

    @abstractmethod
    def update_stage(self, stage_id: str, updates: dict) -> None:
        """更新指定流程阶段的字段（部分更新）。

        Args:
            stage_id: 要更新的阶段唯一标识符。
            updates: 需要更新的字段字典（键为字段名，值为新内容）。
        """
        ...

    @abstractmethod
    def delete_stage(self, stage_id: str) -> bool:
        """删除指定流程阶段。

        Args:
            stage_id: 要删除的阶段唯一标识符。

        Returns:
            bool: True 表示删除成功，False 表示阶段不存在。
        """
        ...

    @abstractmethod
    def save(self) -> None:
        """将内存中的全部数据原子写入 JSON 文件。"""
        ...

    @abstractmethod
    def reload(self) -> None:
        """重新从文件加载数据到内存（用于恢复操作后刷新）。"""
        ...


# ============================================================================
# IProjectService —— 项目管理服务的抽象接口
# ============================================================================

class IProjectService(ABC):
    """项目管理服务的抽象接口。

    定义项目 CRUD 和阶段移动操作的统一契约，UI 层通过本接口
    调用项目业务逻辑，不依赖具体实现类。
    """

    @abstractmethod
    def get_all_projects(self) -> list["Project"]:
        """获取所有项目的 Project 对象列表，按创建时间升序排列。

        Returns:
            list[Project]: 按创建时间升序排列的 Project 对象列表。
        """
        ...

    @abstractmethod
    def get_project_by_id(self, project_id: str) -> Optional["Project"]:
        """根据项目ID获取单个 Project 对象。

        Args:
            project_id: 项目的唯一标识符。

        Returns:
            Project | None: 匹配的 Project 对象，未找到时返回 None。
        """
        ...

    @abstractmethod
    def create_project(self, company_name: str, system_name: str,
                       cert_number: str, issue_date: str, level: str,
                       location: str, deadline: str, notes: str,
                       stage_id: str) -> tuple[bool, str, Optional["Project"]]:
        """创建新的等保测评项目。

        Args:
            company_name: 被测评单位的公司名称。
            system_name: 被测信息系统名称。
            cert_number: 备案证书编号（可选）。
            issue_date: 证书颁发日期。
            level: 系统保护等级。
            location: 项目所在地。
            deadline: 项目截止日期。
            notes: 备注信息。
            stage_id: 初始流程阶段ID。

        Returns:
            tuple[bool, str, Project | None]: (成功与否, 消息, 创建的Project对象或None)。
        """
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
        """更新现有项目的部分字段（支持部分更新）。

        Args:
            project_id: 要更新的项目唯一标识符。
            company_name: 新的公司名称（None 表示保持不变）。
            system_name: 新的系统名称（None 表示保持不变）。
            cert_number: 新的证书编号（None 表示保持不变）。
            issue_date: 新的颁发日期（None 表示保持不变）。
            level: 新的保护等级（None 表示保持不变）。
            location: 新的所在地（None 表示保持不变）。
            deadline: 新的截止日期（None 表示保持不变）。
            notes: 新的备注（None 表示保持不变）。
            stage_id: 新的阶段ID（None 表示保持不变）。
            folder_path: 新的文件夹路径（None 表示保持不变）。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        ...

    @abstractmethod
    def delete_project(self, project_id: str) -> tuple[bool, str]:
        """删除指定项目（不可逆操作）。

        Args:
            project_id: 要删除的项目唯一标识符。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        ...

    @abstractmethod
    def move_project(self, project_id: str,
                     new_stage_id: str) -> tuple[bool, str]:
        """将项目移动到新的流程阶段。

        Args:
            project_id: 要移动的项目唯一标识符。
            new_stage_id: 目标流程阶段ID。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        ...


# ============================================================================
# ILogService —— 日志追踪服务的抽象接口
# ============================================================================

class ILogService(ABC):
    """日志追踪服务的抽象接口。

    定义操作日志的记录和查询契约，上层模块通过本接口访问
    日志功能，不依赖具体实现。
    """

    @abstractmethod
    def add_log(self, action: str, detail: str,
                project_id: str = "", project_name: str = "",
                from_stage: str = "", to_stage: str = "") -> None:
        """记录一条操作日志到持久化存储。

        Args:
            action: 操作类型标识（如：新增项目、阶段变更、编辑流程等）。
            detail: 操作的详细描述文本。
            project_id: 关联的项目唯一标识符（非项目操作时可为空）。
            project_name: 关联的项目显示名称（非项目操作时可为空）。
            from_stage: 阶段变更前的阶段名称（仅阶段变更时填写）。
            to_stage: 阶段变更后的阶段名称（仅阶段变更时填写）。
        """
        ...

    @abstractmethod
    def get_all_logs(self) -> list[dict]:
        """获取全部操作日志（无数量限制）。

        Returns:
            list[dict]: 所有日志条目的字典列表，按时间倒序排列。
        """
        ...

    @abstractmethod
    def get_project_logs(self, project_id: str) -> list[dict]:
        """获取指定项目的操作历史日志。

        Args:
            project_id: 目标项目的唯一标识符。

        Returns:
            list[dict]: 该项目相关的所有日志条目列表。
        """
        ...

    @abstractmethod
    def create_log_callback(self) -> Callable[..., None]:
        """创建一个日志回调函数，供其他业务服务使用。

        通过回调机制实现服务间解耦：业务服务不需要直接持有
        LogService 的引用即可记录日志。

        Returns:
            Callable: 签名为 (action, detail, **kwargs) 的回调函数。
        """
        ...


# ============================================================================
# IWorkflowService —— 流程管理服务的抽象接口（原则 #2 DIP）
# ============================================================================

class IWorkflowService(ABC):
    """流程管理服务的抽象接口。

    定义流程阶段（看板列）的增删改查、排序、重置等完整操作契约。
    UI 层通过本接口调用流程业务逻辑，不依赖具体实现类。
    """

    @abstractmethod
    def get_all_stages(self) -> list:
        """获取所有流程阶段对象列表，按 order 升序排列。

        Returns:
            list: 按 order 升序排列的阶段对象列表。
        """
        ...

    @abstractmethod
    def get_stage_by_id(self, stage_id: str):
        """根据阶段ID获取单个阶段对象。

        Args:
            stage_id: 流程阶段的唯一标识符。

        Returns:
            匹配的阶段对象，未找到时返回 None。
        """
        ...

    @abstractmethod
    def get_first_stage_id(self) -> str:
        """获取第一个阶段的ID（order 最小的阶段）。

        Returns:
            str: 第一个阶段的ID，没有阶段时返回空字符串。
        """
        ...

    @abstractmethod
    def get_stage_name(self, stage_id: str) -> str:
        """根据阶段ID获取阶段的可读名称。

        Args:
            stage_id: 流程阶段唯一标识符。

        Returns:
            str: 阶段的显示名称，未找到时返回"未知阶段"。
        """
        ...

    @abstractmethod
    def add_stage(self, name: str, color: str = "#3498db") -> tuple:
        """添加新的流程阶段。

        Args:
            name: 新阶段的显示名称。
            color: 新阶段的标识颜色（十六进制颜色码）。

        Returns:
            tuple[bool, str, WorkflowStage | None]: (成功, 消息, 新阶段对象或None)。
        """
        ...

    @abstractmethod
    def update_stage_width(self, stage_id: str, column_width: int) -> None:
        """更新阶段的列宽（便捷方法）。

        Args:
            stage_id: 目标阶段唯一标识符。
            column_width: 新的列宽值（像素单位）。
        """
        ...

    @abstractmethod
    def update_stage(self, stage_id: str,
                     name: Optional[str] = None,
                     color: Optional[str] = None) -> tuple:
        """更新阶段的基本信息（名称和/或颜色）。

        Args:
            stage_id: 要更新的阶段唯一标识符。
            name: 新的阶段名称（None 表示不修改）。
            color: 新的标识颜色（None 表示不修改）。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        ...

    @abstractmethod
    def delete_stage(self, stage_id: str) -> tuple:
        """删除指定流程阶段。

        Args:
            stage_id: 要删除的阶段唯一标识符。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        ...

    @abstractmethod
    def reorder_stages(self, stage_ids: list[str]) -> tuple:
        """重新排序流程阶段（看板列拖拽排序）。

        Args:
            stage_ids: 按新顺序排列的阶段ID列表。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        ...

    @abstractmethod
    def reset_to_default(self) -> tuple:
        """重置为系统默认的流程配置。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
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
            bool: True 表示底层依赖（pywin32）已安装，服务可用；False 表示不可用。
        """
        ...


# ============================================================================
# OleEmbedError —— OLE 嵌入异常（原则 #7 显式异常）
# ============================================================================

class OleEmbedError(Exception):
    """OLE 对象嵌入过程中发生的异常。"""
    pass
