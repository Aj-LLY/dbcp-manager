"""
日志工具模块 - 提供操作日志的记录、读取和格式化功能

设计为独立工具类，不依赖其他业务模块，可在任何层级调用
"""

import os  # 操作系统接口模块，用于文件路径操作和目录创建
import json  # JSON序列化模块，用于日志数据的持久化存储
import time  # 时间模块，用于生成日志ID（毫秒级时间戳）
from datetime import datetime  # 日期时间模块，用于格式化日志时间戳


class OperationLogger:
    """操作日志记录器
    负责将用户操作记录到内存和文件中，支持日志查看和导出
    内存中维护完整日志列表，每次写操作同时持久化到文件
    """

    def __init__(self, log_file_path: str):
        """初始化日志记录器

        Args:
            log_file_path: 日志文件的完整路径（如 data/operation_log.json）
        """
        self._log_file_path = log_file_path  # 保存日志文件路径，后续读写均基于此路径
        self._logs: list[dict] = []  # 内存中的日志列表，存储所有操作日志字典
        self._load_from_file()  # 从文件中加载已有的历史日志

    def _load_from_file(self):
        """从文件加载历史日志
        如果文件不存在或文件内容损坏，则初始化为空列表
        """
        if os.path.exists(self._log_file_path):  # 检查日志文件是否存在
            try:
                with open(self._log_file_path, 'r', encoding='utf-8') as f:  # 以UTF-8编码打开日志文件
                    self._logs = json.load(f)  # 将JSON文件内容解析为Python列表
            except (json.JSONDecodeError, IOError):  # JSON格式错误或文件读取错误
                self._logs = []  # 容错：初始化为空列表

    def _save_to_file(self):
        """将日志列表持久化到文件
        确保日志目录存在，以UTF-8编码写入，使用缩进格式提升可读性
        """
        os.makedirs(os.path.dirname(self._log_file_path), exist_ok=True)  # 如果目录不存在则递归创建
        with open(self._log_file_path, 'w', encoding='utf-8') as f:  # 以写入模式打开文件
            json.dump(self._logs, f, ensure_ascii=False, indent=2)  # 写入JSON，保留中文，带缩进格式化

    def add_log(self, action: str, detail: str,
                project_id: str = "", project_name: str = "",
                from_stage: str = "", to_stage: str = ""):
        """添加一条操作日志

        Args:
            action: 操作类型（如：新增项目、拖拽变更、编辑流程等）
            detail: 操作详细描述文本
            project_id: 关联项目ID（可为空，表示非项目相关的系统操作）
            project_name: 关联项目名称
            from_stage: 变更前阶段名称
            to_stage: 变更后阶段名称
        """
        entry = {  # 构建日志条目字典
            "id": str(int(time.time() * 1000)),  # 使用毫秒级时间戳作为日志唯一ID
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 格式化当前时间为时间戳
            "action": action,  # 操作类型
            "detail": detail,  # 操作详细描述
            "project_id": project_id,  # 关联的项目ID
            "project_name": project_name,  # 关联的项目名称
            "from_stage": from_stage,  # 变更前的阶段（如适用）
            "to_stage": to_stage,  # 变更后的阶段（如适用）
        }
        self._logs.append(entry)  # 将新日志条目添加到内存列表末尾
        self._save_to_file()  # 立即持久化到文件，保证数据不丢失

    def get_all_logs(self) -> list[dict]:
        """获取所有操作日志，按时间倒序排列（最新的在前面）"""
        return sorted(self._logs, key=lambda x: x["timestamp"], reverse=True)  # 按时间戳降序排列

    def get_logs_by_project(self, project_id: str) -> list[dict]:
        """获取指定项目的所有操作日志

        Args:
            project_id: 项目唯一标识

        Returns:
            该项目的所有日志条目列表
        """
        return [log for log in self._logs if log["project_id"] == project_id]  # 过滤出匹配项目ID的日志

    def get_recent_logs(self, count: int = 50) -> list[dict]:
        """获取最近N条日志

        Args:
            count: 需要获取的日志条数

        Returns:
            最近count条日志列表
        """
        sorted_logs = self.get_all_logs()  # 先获取全部日志并按时间倒序排列
        return sorted_logs[:count]  # 截取前count条，即最近count条日志

    def clear_logs(self):
        """清空所有日志（危险操作，清空后不可恢复）"""
        self._logs.clear()  # 清空内存中的日志列表
        self._save_to_file()  # 立即持久化空列表到文件
