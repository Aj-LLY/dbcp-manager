"""
日志追踪服务模块 - 统一管理操作日志的记录与查询。

本模块作为业务逻辑层与底层日志存储之间的桥梁，提供面向业务场景的
高层次日志接口。主要职责：

1. 封装底层 OperationLogger 的初始化和配置。
2. 提供语义化的日志记录方法（add_log）。
3. 提供多种查询接口（最近日志、全部日志、按项目筛选）。
4. 生成回调函数供 ProjectService 和 WorkflowService 使用，
   实现服务间的松耦合 —— 业务服务不需要直接持有 LogService 引用。

日志文件路径通过 Config 类自动获取，无需手动指定。
"""

# ---------------------------------------------------------------------------
# 标准库导入
# ---------------------------------------------------------------------------
from typing import Optional
# Optional: 用于类型提示中标记可空值（虽然本模块中未直接使用，但保留以备扩展）

# ---------------------------------------------------------------------------
# 项目内导入（工具层 + 配置层）
# ---------------------------------------------------------------------------
from utils.config import Config
# Config: 系统配置类，提供日志文件路径等全局配置项

from utils.logger import OperationLogger
# OperationLogger: 底层日志记录器，负责日志条目的 JSON 文件读写


class LogService:
    """日志追踪服务。

    封装操作日志的记录和查询逻辑，作为 UI 层与底层日志实现之间的
    抽象层。创建时自动从 Config 获取日志文件路径并初始化底层记录器。

    日志数据结构（由 OperationLogger 保证）:
        - timestamp: 操作时间戳（ISO 8601 格式）。
        - action: 操作类型（新增项目 / 阶段变更 / 编辑流程 等）。
        - detail: 人类可读的操作描述。
        - project_id / project_name: 关联的项目信息。
        - from_stage / to_stage: 阶段变更的前后阶段名称。

    日志文件路径:
        通过 Config.get_log_file_path() 获取，位于用户数据目录下。

    提供的接口：
    - add_log(): 记录一条操作日志。
    - get_recent_logs(): 获取最近的 N 条日志。
    - get_all_logs(): 获取全部操作日志。
    - get_project_logs(): 获取指定项目的操作日志。
    - create_log_callback(): 创建日志回调函数（供其他服务使用）。

    属性说明:
        _logger (OperationLogger): 底层日志记录器实例，负责文件级别的读写。
    """

    def __init__(self):
        """初始化日志服务。

        自动从系统配置中获取日志文件的存储路径，并创建底层 OperationLogger
        实例。日志文件路径由 Config.get_log_file_path() 提供。
        """
        # 从配置获取操作日志文件的完整存储路径
        log_path = Config.get_log_file_path()
        # 创建底层日志记录器实例，绑定到指定文件
        self._logger = OperationLogger(log_path)

    # ========================================================================
    # 日志记录
    # ========================================================================

    def add_log(self, action: str, detail: str,
                project_id: str = "", project_name: str = "",
                from_stage: str = "", to_stage: str = ""):
        """记录一条操作日志到持久化存储。

        对底层 OperationLogger.add_log() 的语义化封装，
        提供更明确的参数名和默认值。

        Args:
            action: 操作类型标识（如：新增项目、阶段变更、编辑流程等）。
                    建议使用 LogEntry 类预定义的 ACTION_* 常量。
            detail: 操作的详细描述文本（人类可读，用于日志列表展示）。
            project_id: 关联的项目唯一标识符（非项目操作时可为空）。
            project_name: 关联的项目显示名称（非项目操作时可为空）。
            from_stage: 阶段变更前的阶段名称（仅阶段变更时填写）。
            to_stage: 阶段变更后的阶段名称（仅阶段变更时填写）。
        """
        import socket
        import uuid
        import getpass
        net_info = f"host={socket.gethostname()} ip={socket.gethostbyname(socket.gethostname())} mac={uuid.getnode():x} user={getpass.getuser()}"
        self._logger.add_log(
            action=action,
            detail=f"{detail} [{net_info}]",
            project_id=project_id,
            project_name=project_name,
            from_stage=from_stage,
            to_stage=to_stage,
        )

    # ========================================================================
    # 日志查询
    # ========================================================================

    def get_recent_logs(self, count: int = 100) -> list[dict]:
        """获取最近的 N 条操作日志。

        用于日志查看界面中展示最新操作记录，默认显示最近 100 条。

        Args:
            count: 需要获取的日志条目数量，默认 100。

        Returns:
            list[dict]: 日志条目字典列表，按时间倒序排列（最新的在前）。
        """
        # 委托底层记录器获取最近日志
        return self._logger.get_recent_logs(count)

    def get_all_logs(self) -> list[dict]:
        """获取全部操作日志（无数量限制）。

        Returns:
            list[dict]: 所有日志条目的字典列表，按时间倒序排列。
        """
        # 委托底层记录器获取全部日志
        return self._logger.get_all_logs()

    def get_project_logs(self, project_id: str) -> list[dict]:
        """获取指定项目的操作历史日志。

        用于项目详情页中展示该项目的完整操作记录（创建、编辑、阶段变更等）。

        Args:
            project_id: 目标项目的唯一标识符。

        Returns:
            list[dict]: 该项目相关的所有日志条目列表。
        """
        # 委托底层记录器按项目ID筛选
        return self._logger.get_logs_by_project(project_id)

    # ========================================================================
    # 回调函数生成（服务解耦）
    # ========================================================================

    def create_log_callback(self):
        """创建一个日志回调函数，供其他业务服务使用。

        通过回调机制实现服务间解耦：
        - ProjectService 和 WorkflowService 不需要直接持有 LogService 的引用。
        - 它们只需在构造函数中接收回调函数，操作完成后调用即可。
        - LogService 保持独立，不依赖其他业务服务。

        Returns:
            Callable: 签名为 (action, detail, **kwargs) 的回调函数。
                      调用时自动提取 kwargs 中的可选参数并转发给 add_log()。
        """
        def callback(action: str = "", detail: str = "", **kwargs):
            """日志回调函数（闭包）。

            从关键字参数中提取日志所需的可选字段，缺失时使用空字符串作为默认值。
            这样可以灵活支持不同业务服务的日志记录需求，避免所有调用方
            都必须传入完整的参数列表。

            Args:
                action: 操作类型标识。
                detail: 操作详细描述。
                **kwargs: 可选参数，支持 project_id, project_name, from_stage, to_stage。
            """
            # 从 kwargs 中提取可选参数，缺失时使用空字符串
            self.add_log(
                action=action,
                detail=detail,
                project_id=kwargs.get("project_id", ""),
                project_name=kwargs.get("project_name", ""),
                from_stage=kwargs.get("from_stage", ""),
                to_stage=kwargs.get("to_stage", ""),
            )

        # 返回创建的回调函数，供其他服务持有和调用
        return callback
