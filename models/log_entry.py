"""
操作日志实体模块 - 定义操作日志条目模型，用于追踪项目每一次变更操作。

本模块提供 LogEntry 类，封装单个操作日志的完整信息，包括：
- 操作类型（预定义常量：新增项目、编辑项目、删除项目、阶段变更、编辑流程等）
- 操作时间戳
- 操作详细描述
- 关联的项目信息（ID 和名称）
- 阶段变更时的前后阶段名称

同时提供字典序列化/反序列化能力，用于 JSON 持久化存储和日志查看。
"""

# ---------------------------------------------------------------------------
# 项目内导入（自建工具库）
# ---------------------------------------------------------------------------
from utils.helpers import generate_id, get_now_str
# generate_id: 生成带有指定前缀的唯一标识符
# get_now_str: 获取当前时间的格式化字符串，用于设置日志时间戳


class LogEntry:
    """操作日志条目实体类。

    每条 LogEntry 实例记录用户的一次操作行为，支持：
    - 项目操作追踪（CRUD 事件）
    - 流程阶段变更追踪（拖拽、箭头移动、详情编辑等）
    - 流程配置变更追踪（阶段增删、排序调整等）

    属性说明:
        id (str): 日志条目唯一标识，格式为 "log_" 前缀加时间戳哈希。
        timestamp (str): 操作发生时间，格式为 YYYY-MM-DD HH:MM:SS。
        action (str): 操作类型，建议使用类预定义常量（ACTION_*）。
        detail (str): 操作详细描述文本，用于日志列表中展示。
        project_id (str): 关联的项目唯一标识（系统级操作时可为空）。
        project_name (str): 关联的项目显示名称，用于直接展示免去二次查询。
        from_stage (str): 阶段变更前的阶段名称（非阶段变更时为空）。
        to_stage (str): 阶段变更后的阶段名称（非阶段变更时为空）。
    """

    # ========================================================================
    # 预定义操作类型常量
    # 统一管理所有可能的操作类型，便于扩展和 UI 层过滤显示
    # ========================================================================

    ACTION_CREATE = "新增项目"              # 创建新项目时的操作类型标识
    ACTION_EDIT = "编辑项目"                # 修改项目信息（不含阶段变更）时的操作类型标识
    ACTION_DELETE = "删除项目"              # 删除项目时的操作类型标识
    ACTION_MOVE = "阶段变更"                # 项目阶段发生变更时的操作类型标识
    ACTION_WORKFLOW_UPDATE = "编辑流程"     # 修改流程阶段配置时的操作类型标识
    ACTION_STAGE_ADD = "新增阶段"           # 添加新的流程阶段时的操作类型标识
    ACTION_STAGE_DELETE = "删除阶段"        # 删除流程阶段时的操作类型标识

    def __init__(self, action: str = "", detail: str = "",
                 project_id: str = "", project_name: str = "",
                 from_stage: str = "", to_stage: str = "",
                 entry_id: str = "", timestamp: str = ""):
        """初始化日志条目对象。

        Args:
            action: 操作类型字符串，建议使用类常量 ACTION_* 的值以保证一致性。
            detail: 操作详细描述，用于在日志列表中展示可读的说明文字。
            project_id: 关联的项目唯一标识ID。
            project_name: 关联项目的显示名称。
            from_stage: 阶段变更前的阶段名称（仅阶段变更时填写）。
            to_stage: 阶段变更后的阶段名称（仅阶段变更时填写）。
            entry_id: 已有日志ID（反序列化时传入），为空则自动生成以 "log" 为前缀的新ID。
            timestamp: 已有时间戳（反序列化时传入），为空则使用当前系统时间。
        """
        # 日志ID：优先使用传入的已有ID，否则自动生成以 "log" 为前缀的唯一ID
        self.id = entry_id or generate_id("log")

        # 时间戳：优先使用传入的已有时间，否则使用当前系统时间
        self.timestamp = timestamp or get_now_str()

        # ---- 日志核心字段 ----
        self.action = action            # 操作类型（如：新增项目、阶段变更等）
        self.detail = detail            # 操作详细描述（人类可读文本）
        self.project_id = project_id    # 关联项目ID（用于按项目筛选日志）
        self.project_name = project_name  # 关联项目名称（避免列表展示时的二次查询）
        self.from_stage = from_stage    # 变更前的阶段名称（阶段变更日志专用）
        self.to_stage = to_stage        # 变更后的阶段名称（阶段变更日志专用）

    # ========================================================================
    # 序列化 / 反序列化
    # ========================================================================

    def to_dict(self) -> dict:
        """将日志对象序列化为字典，用于 JSON 持久化存储。

        Returns:
            dict: 包含日志所有属性的字典，键名为 JSON 存储字段名。
        """
        return {
            "id": self.id,                     # 日志唯一标识
            "timestamp": self.timestamp,       # 操作发生时间
            "action": self.action,             # 操作类型
            "detail": self.detail,             # 操作详细描述
            "project_id": self.project_id,     # 关联项目ID
            "project_name": self.project_name, # 关联项目名称
            "from_stage": self.from_stage,     # 变更前阶段（阶段变更时使用）
            "to_stage": self.to_stage,         # 变更后阶段（阶段变更时使用）
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LogEntry":
        """从字典反序列化创建日志对象。

        Args:
            data: 包含日志属性的字典，通常从 JSON 日志文件解析而来。

        Returns:
            LogEntry: 反序列化后的日志条目对象。
        """
        return cls(
            action=data.get("action", ""),             # 提取操作类型
            detail=data.get("detail", ""),             # 提取操作描述
            project_id=data.get("project_id", ""),     # 提取关联项目ID
            project_name=data.get("project_name", ""), # 提取关联项目名称
            from_stage=data.get("from_stage", ""),     # 提取变更前阶段
            to_stage=data.get("to_stage", ""),         # 提取变更后阶段
            entry_id=data.get("id", ""),               # 提取已有日志ID
            timestamp=data.get("timestamp", ""),       # 提取已有时间戳
        )

    # ========================================================================
    # 调试输出
    # ========================================================================

    def __repr__(self) -> str:
        """对象的调试字符串表示，便于开发调试时快速查看日志概要。

        Returns:
            str: 包含操作类型、项目名称和时间的简要描述。
        """
        return (f"LogEntry(action={self.action}, project={self.project_name}, "
                f"time={self.timestamp})")
