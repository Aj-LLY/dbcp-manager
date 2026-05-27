"""
日志追踪服务 - 统一管理操作日志的记录和查询

作为业务层与日志工具之间的桥梁，提供面向业务场景的日志接口。
隔离了底层日志存储实现（OperationLogger），业务服务通过回调方式使用。
"""

from typing import Optional  # 类型提示模块，用于标记可选类型
from utils.logger import OperationLogger  # 导入底层日志记录器
from utils.config import Config  # 导入配置类，用于获取日志文件路径


class LogService:
    """日志追踪服务
    封装操作日志的记录和查询逻辑，为UI层提供简洁的日志访问接口。
    创建时自动从配置获取日志文件路径并初始化底层记录器。
    """

    def __init__(self):
        """初始化日志服务，创建日志记录器实例
        日志文件路径通过 Config 类自动获取
        """
        log_path = Config.get_log_file_path()  # 从配置获取操作日志文件的完整路径
        self._logger = OperationLogger(log_path)  # 创建底层日志记录器实例

    def add_log(self, action: str, detail: str,
                project_id: str = "", project_name: str = "",
                from_stage: str = "", to_stage: str = ""):
        """记录一条操作日志
        对底层记录器的封装，提供更友好的接口

        Args:
            action: 操作类型（如：新增项目、拖拽变更等）
            detail: 操作的详细描述
            project_id: 关联的项目ID
            project_name: 关联的项目名称
            from_stage: 变更前阶段名称
            to_stage: 变更后阶段名称
        """
        self._logger.add_log(  # 委托底层记录器写入日志
            action=action,
            detail=detail,
            project_id=project_id,
            project_name=project_name,
            from_stage=from_stage,
            to_stage=to_stage,
        )

    def get_recent_logs(self, count: int = 100) -> list[dict]:
        """获取最近的N条日志（用于日志查看界面）

        Args:
            count: 需要获取的日志条数，默认100条

        Returns:
            日志条目字典列表，按时间倒序
        """
        return self._logger.get_recent_logs(count)  # 委托底层记录器获取最近日志

    def get_all_logs(self) -> list[dict]:
        """获取全部操作日志（按时间倒序）"""
        return self._logger.get_all_logs()  # 委托底层记录器获取全部日志

    def get_project_logs(self, project_id: str) -> list[dict]:
        """获取指定项目的操作日志（用于项目详情中的操作历史）

        Args:
            project_id: 项目唯一标识

        Returns:
            该项目的所有日志条目列表
        """
        return self._logger.get_logs_by_project(project_id)  # 委托底层记录器按项目筛选

    def create_log_callback(self):
        """创建一个回调函数，供其他服务（ProjectService, WorkflowService）调用以记录日志

        通过回调函数解耦服务之间的依赖（日志服务不需要被其他服务直接持有），
        其他服务只需在操作完成后调用此回调即可自动记录日志。

        Returns:
            签名为 (action, detail, **kwargs) 的回调函数
        """
        def callback(action: str = "", detail: str = "", **kwargs):
            """日志回调函数
            从kwargs中提取可选的日志参数，缺失时使用默认值
            """
            self.add_log(  # 调用自身的add_log方法
                action=action,
                detail=detail,
                project_id=kwargs.get("project_id", ""),     # 提取项目ID
                project_name=kwargs.get("project_name", ""), # 提取项目名称
                from_stage=kwargs.get("from_stage", ""),     # 提取变更前阶段
                to_stage=kwargs.get("to_stage", ""),         # 提取变更后阶段
            )
        return callback  # 返回创建的回调函数
