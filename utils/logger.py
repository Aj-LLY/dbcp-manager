"""
日志工具模块 - 提供操作日志的记录、读取、查询和持久化功能

本模块实现操作日志的完整管理，所有用户操作（新增项目、编辑流程、拖拽变更等）
均通过 OperationLogger 记录到内存和 JSON 文件中。

核心功能：
  1. add_log()：添加一条操作日志（内存 + 文件双写）
  2. get_all_logs()：获取所有日志（按时间倒序排列）
  3. get_logs_by_project()：获取指定项目的专属日志
  4. get_recent_logs()：获取最近 N 条日志
  5. clear_logs()：清空所有日志（危险操作）

日志数据结构（每条日志为一个 dict）：
  {
      "id": "1717372800123",            # 日志唯一 ID（毫秒时间戳）
      "timestamp": "2026-06-03 14:30:25", # 操作时间（标准日期时间格式）
      "action": "新增项目",               # 操作类型（如 新增/编辑/删除/移动）
      "detail": "创建项目 XXX",           # 详细描述文本
      "project_id": "proj_xxx",          # 关联项目 ID（空字符串表示系统级操作）
      "project_name": "项目名称",        # 关联项目显示名称
      "from_stage": "项目启动",          # 变更前阶段（阶段移动操作）
      "to_stage": "差距评估",            # 变更后阶段（阶段移动操作）
  }

设计特点：
  - 内存优先：所有操作先写入内存列表，立即响应
  - 即时持久化：每次 add_log 都写入文件，防止崩溃丢失数据
  - 容错设计：文件损坏或不存在时初始化为空列表，不影响用户使用
  - 时间排序：get_all_logs 按时间倒序（最新的在前）排列

依赖：
  - os / json / time / datetime：Python 标准库
  - 无项目内部模块依赖，可独立使用
"""

# =============================================================================
# 导入区
# =============================================================================

import os  # 操作系统接口模块，用于文件路径检查和目录创建
import json  # JSON 序列化模块，用于日志数据的文件读写
import time  # 时间模块，用于生成基于毫秒时间戳的日志唯一 ID
from datetime import datetime  # 日期时间模块，用于格式化日志时间戳字段


class OperationLogger:
    """操作日志记录器 - 管理所有系统操作日志的内存缓存和文件持久化

    采用"内存 + 文件"双存储模式：
      - 内存（self._logs）：快速读取和查询，避免频繁文件 IO
      - 文件（operation_log.json）：持久化存储，保证数据不丢失

    每次写操作（add_log / clear_logs）都会同时更新内存和文件，
    读操作（get_all_logs / get_logs_by_project / get_recent_logs）仅从内存读取。

    Attributes:
        _log_file_path (str): 日志文件的完整路径
        _logs (list[dict]): 内存中的日志列表，每个元素为一条日志字典
    """

    def __init__(self, log_file_path: str):
        """初始化日志记录器 - 设置文件路径并从文件加载历史日志

        Args:
            log_file_path: 日志文件的完整路径，如 "C:/.../data/operation_log.json"
        """
        self._log_file_path = log_file_path  # 保存日志文件完整路径，后续读写均基于此路径
        self._logs: list[dict] = []  # 初始化内存日志列表为空列表
        self._load_from_file()  # 尝试从文件中加载已有的历史日志（文件不存在则保持空列表）

    # =============================================================================
    # 文件读写 - 内部方法，外部不应直接调用
    # =============================================================================

    def _load_from_file(self):
        """从 JSON 文件加载历史日志到内存

        如果文件不存在或内容损坏（JSON 格式错误、编码问题等），
        安全地初始化为空列表，不向上层抛出异常。
        """
        if os.path.exists(self._log_file_path):  # 检查日志文件是否存在
            try:
                with open(self._log_file_path, 'r', encoding='utf-8') as f:  # UTF-8 编码打开文件
                    self._logs = json.load(f)  # 将 JSON 数组解析为 Python 列表
            except (json.JSONDecodeError, IOError):  # JSON 格式错误 | 文件读取失败
                self._logs = []  # 容错处理：初始化为空列表，不影响程序正常运行

    def _save_to_file(self):
        """将内存中的日志列表持久化到 JSON 文件

        写入策略：
          - 先确保目标目录存在（递归创建）
          - 以 UTF-8 编码写入，保留中文字符（ensure_ascii=False）
          - 使用 2 空格缩进格式化，提升可读性
        """
        os.makedirs(os.path.dirname(self._log_file_path), exist_ok=True)  # 递归创建目录（exist_ok 避免重复报错）
        with open(self._log_file_path, 'w', encoding='utf-8') as f:  # 以写入模式打开文件
            json.dump(self._logs, f, ensure_ascii=False, indent=2)  # 保留中文，2 空格缩进格式化

    # =============================================================================
    # 日志写入
    # =============================================================================

    def add_log(self, action: str, detail: str,
                project_id: str = "", project_name: str = "",
                from_stage: str = "", to_stage: str = ""):
        """添加一条新的操作日志

        每次用户执行一个业务操作（新增/编辑/删除/移动项目、编辑流程等），
        由服务层通过 log_callback 调用此方法记录。

        Args:
            action: 操作类型描述，如 "新增项目"、"编辑流程"、"拖拽变更"、"删除项目"
            detail: 操作详细描述文本，如 "创建项目 XXX有限公司-ERP系统"
            project_id: 关联的项目唯一 ID（非项目相关操作时留空）
            project_name: 关联的项目显示名称（用于日志查看时展示）
            from_stage: 操作前的阶段名称（阶段移动操作使用，其他操作留空）
            to_stage: 操作后的阶段名称（阶段移动操作使用，其他操作留空）
        """
        # 构建日志条目字典
        entry = {
            "id": str(int(time.time() * 1000)),  # 日志唯一 ID：毫秒级时间戳转字符串
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 操作时间戳：标准格式
            "action": action,  # 操作类型
            "detail": detail,  # 详细描述
            "project_id": project_id,  # 关联项目 ID
            "project_name": project_name,  # 关联项目名称
            "from_stage": from_stage,  # 变更前阶段
            "to_stage": to_stage,  # 变更后阶段
        }
        self._logs.append(entry)  # 追加到内存列表末尾
        self._save_to_file()  # 立即持久化到文件（保证数据不丢失）

    # =============================================================================
    # 日志查询
    # =============================================================================

    def get_all_logs(self) -> list[dict]:
        """获取所有操作日志，按时间从新到旧排列

        Returns:
            list[dict]: 按 timestamp 降序排列的日志列表（最新的在前面）
        """
        return sorted(self._logs, key=lambda x: x["timestamp"], reverse=True)  # 按时间戳降序排列

    def get_logs_by_project(self, project_id: str) -> list[dict]:
        """获取指定项目的所有操作日志

        过滤出 project_id 字段与参数匹配的日志条目。
        可用于在项目详情窗口中展示该项目的操作历史。

        Args:
            project_id: 项目的唯一标识符（UUID 字符串）

        Returns:
            list[dict]: 该项目的所有日志条目列表（保持原始插入顺序）
        """
        return [log for log in self._logs if log["project_id"] == project_id]  # 列表推导式过滤

    def get_recent_logs(self, count: int = 50) -> list[dict]:
        """获取最近 N 条操作日志

        用于日志查看对话框，展示最新的操作记录。

        Args:
            count: 需要获取的日志条数（默认 50）

        Returns:
            list[dict]: 最近 count 条日志列表，按时间降序排列
        """
        sorted_logs = self.get_all_logs()  # 先获取全部日志并排序
        return sorted_logs[:count]  # 取前 count 条（即最近 count 条）

    # =============================================================================
    # 日志管理
    # =============================================================================

    def clear_logs(self):
        """清空所有操作日志（不可逆操作）

        此操作会同时清空内存和文件中的所有日志数据。
        通常在管理员需要重置日志时使用，或作为系统维护工具。
        调用后数据无法恢复，使用时需谨慎。
        """
        self._logs.clear()  # 清空内存中的日志列表
        self._save_to_file()  # 立即持久化空列表到文件（覆盖原有内容）
