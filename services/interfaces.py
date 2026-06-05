"""
服务层抽象接口定义 - 依赖倒置原则 (DIP) 实现。

本模块定义服务层的抽象基类 (ABC)，上层模块（如 UI 层）应依赖这些
抽象接口而非具体实现类，从而实现依赖倒置（Dependency Inversion Principle）。

接口定义规范：
- 使用 abc.ABC 作为抽象基类。
- 使用 @abstractmethod 装饰器标记需要子类实现的方法。
- 每个抽象方法只声明签名和文档字符串，不包含任何实现逻辑。
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

    定义项目数据和流程阶段数据的底层 CRUD 操作签名。
    所有数据持久化的具体实现类都必须实现此接口的全部方法。
    """

    @abstractmethod
    def get_all_projects(self) -> list[dict]:
        """获取所有项目的字典列表。

        Returns:
            list[dict]: 项目字典列表。
        """
        ...

    @abstractmethod
    def get_project_by_id(self, project_id: str) -> Optional[dict]:
        """根据项目ID查找单个项目。

        Args:
            project_id: 项目唯一标识符。

        Returns:
            dict | None: 匹配的项目字典，未找到时返回 None。
        """
        ...

    @abstractmethod
    def add_project(self, project_dict: dict) -> None:
        """向数据中添加新项目。

        Args:
            project_dict: 项目完整字段字典。
        """
        ...

    @abstractmethod
    def update_project(self, project_id: str, updates: dict) -> None:
        """更新指定项目的字段。

        Args:
            project_id: 要更新的项目唯一标识符。
            updates: 需要更新的字段字典。
        """
        ...

    @abstractmethod
    def delete_project(self, project_id: str) -> bool:
        """删除指定项目。

        Args:
            project_id: 要删除的项目唯一标识符。

        Returns:
            bool: True 表示删除成功，False 表示未找到匹配的项目。
        """
        ...

    @abstractmethod
    def get_all_stages(self) -> list[dict]:
        """获取所有流程阶段的字典列表。

        Returns:
            list[dict]: 按 order 升序排列的阶段字典列表。
        """
        ...

    @abstractmethod
    def replace_all_stages(self, stages_list: list[dict]) -> None:
        """替换全部流程阶段（批量更新操作）。

        Args:
            stages_list: 新的阶段字典列表。
        """
        ...

    @abstractmethod
    def save(self) -> None:
        """将内存中的全部数据持久化到文件。"""
        ...

    @abstractmethod
    def reload(self) -> None:
        """重新从文件加载数据到内存。"""
        ...


# ============================================================================
# IProjectService —— 项目管理服务的抽象接口
# ============================================================================

class IProjectService(ABC):
    """项目管理服务的抽象接口。

    定义项目相关的所有业务操作签名，包括增删改查和阶段移动。
    上层模块应依赖此接口而非具体的 ProjectService 实现。
    """

    @abstractmethod
    def get_all_projects(self) -> list["Project"]:
        """获取所有项目的实体对象列表。

        Returns:
            list[Project]: 按创建时间升序排列的 Project 对象列表。
        """
        ...

    @abstractmethod
    def get_project_by_id(self, project_id: str) -> Optional["Project"]:
        """根据项目ID获取单个项目实体对象。

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
            cert_number: 备案证书编号。
            issue_date: 证书颁发日期。
            level: 系统保护等级。
            location: 项目所在地。
            deadline: 项目截止日期。
            notes: 备注信息。
            stage_id: 初始流程阶段ID。

        Returns:
            tuple[bool, str, Project | None]: (是否成功, 消息, 创建的Project或None)。
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
        """更新现有项目的部分字段。

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
        """删除指定项目。

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

    定义操作日志的记录和查询操作签名。
    通过回调机制实现与业务服务之间的松耦合。
    """

    @abstractmethod
    def add_log(self, action: str, detail: str,
                project_id: str = "", project_name: str = "",
                from_stage: str = "", to_stage: str = "") -> None:
        """记录一条操作日志。

        Args:
            action: 操作类型标识。
            detail: 操作的详细描述文本。
            project_id: 关联的项目唯一标识符。
            project_name: 关联的项目显示名称。
            from_stage: 阶段变更前的阶段名称。
            to_stage: 阶段变更后的阶段名称。
        """
        ...

    @abstractmethod
    def get_all_logs(self) -> list[dict]:
        """获取全部操作日志。

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

        通过回调机制实现服务间解耦：业务服务不直接持有 LogService 引用。

        Returns:
            Callable: 签名为 (action, detail, **kwargs) 的回调函数。
        """
        ...
