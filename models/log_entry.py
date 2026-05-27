"""
操作日志实体类 - 记录每一次项目进度变更操作

用于追踪操作历史，支持日志查看和审计追溯
"""

from utils.helpers import generate_id, get_now_str  # 导入ID生成函数和当前时间获取函数


class LogEntry:
    """操作日志条目实体
    每条日志记录用户的一次操作行为，包括操作类型、描述、关联项目等

    Attributes:
        id: 日志条目唯一标识（基于时间戳自动生成）
        timestamp: 操作发生的时间戳（YYYY-MM-DD HH:MM:SS格式）
        action: 操作类型（如：新增项目、拖拽变更、编辑项目等）
        detail: 操作详细描述文本
        project_id: 关联的项目ID（系统级操作可为空）
        project_name: 关联的项目名称，便于直接展示
        from_stage: 变更前的阶段名称（阶段变更操作时填写）
        to_stage: 变更后的阶段名称（阶段变更操作时填写）
    """

    # 预定义操作类型常量（便于统一管理和扩展新的操作类型）
    ACTION_CREATE = "新增项目"           # 创建新项目时的操作类型
    ACTION_EDIT = "编辑项目"             # 编辑项目信息时的操作类型
    ACTION_DELETE = "删除项目"           # 删除项目时的操作类型
    ACTION_MOVE = "拖拽变更"             # 拖拽项目卡片到其他阶段时的操作类型
    ACTION_WORKFLOW_UPDATE = "编辑流程"  # 修改流程阶段配置时的操作类型
    ACTION_STAGE_ADD = "新增阶段"        # 添加新流程阶段时的操作类型
    ACTION_STAGE_DELETE = "删除阶段"     # 删除流程阶段时的操作类型

    def __init__(self, action: str = "", detail: str = "",
                 project_id: str = "", project_name: str = "",
                 from_stage: str = "", to_stage: str = "",
                 entry_id: str = "", timestamp: str = ""):
        """初始化日志条目

        Args:
            action: 操作类型（建议使用类常量 ACTION_* 的值）
            detail: 操作详细描述
            project_id: 关联项目ID
            project_name: 关联项目名称
            from_stage: 变更前阶段名称
            to_stage: 变更后阶段名称
            entry_id: 条目ID（为空时自动生成以 "log" 为前缀的新ID）
            timestamp: 时间戳（为空时使用当前系统时间）
        """
        self.id = entry_id or generate_id("log")  # 使用传入ID或生成以 "log" 为前缀的新ID
        self.timestamp = timestamp or get_now_str()  # 使用传入的时间戳或获取当前时间
        self.action = action            # 操作类型
        self.detail = detail            # 操作详细描述
        self.project_id = project_id    # 关联项目ID
        self.project_name = project_name  # 关联项目名称
        self.from_stage = from_stage    # 变更前的阶段
        self.to_stage = to_stage        # 变更后的阶段

    def to_dict(self) -> dict:
        """将日志对象序列化为字典，便于JSON存储"""
        return {
            "id": self.id,                     # 日志ID
            "timestamp": self.timestamp,       # 操作时间
            "action": self.action,             # 操作类型
            "detail": self.detail,             # 操作描述
            "project_id": self.project_id,     # 关联项目ID
            "project_name": self.project_name, # 关联项目名称
            "from_stage": self.from_stage,     # 变更前阶段
            "to_stage": self.to_stage,         # 变更后阶段
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LogEntry":
        """从字典反序列化创建日志对象

        Args:
            data: 包含日志属性的字典（通常来自JSON数据）

        Returns:
            反序列化后的LogEntry对象
        """
        return cls(
            action=data.get("action", ""),           # 提取操作类型
            detail=data.get("detail", ""),           # 提取操作描述
            project_id=data.get("project_id", ""),   # 提取项目ID
            project_name=data.get("project_name", ""), # 提取项目名称
            from_stage=data.get("from_stage", ""),   # 提取变更前阶段
            to_stage=data.get("to_stage", ""),       # 提取变更后阶段
            entry_id=data.get("id", ""),             # 提取日志ID
            timestamp=data.get("timestamp", ""),     # 提取时间戳
        )

    def __repr__(self) -> str:
        """对象的字符串表示，用于调试输出"""
        return (f"LogEntry(action={self.action}, project={self.project_name}, "
                f"time={self.timestamp})")  # 格式化显示操作类型、项目和时间的概要
