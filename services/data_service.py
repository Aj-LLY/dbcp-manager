"""
数据持久化服务 - 负责所有数据的JSON文件读写操作

是整个系统的数据层，所有业务服务通过它来存取数据。
采用单例模式确保全局只有一个数据服务实例。

设计要点：
- 文件级别的原子写入（先写临时文件再替换）
- 支持默认数据初始化
- 提供统一的数据访问接口
"""

import os  # 操作系统接口模块，用于目录创建和文件存在性检查
import json  # JSON序列化模块，用于数据的持久化存储
import tempfile  # 临时文件模块，用于实现原子写入（先写临时文件再替换）
from typing import Optional  # 类型提示模块，用于标记可选返回值类型


class DataService:
    """数据持久化服务（单例模式）
    使用单例模式确保整个应用只有一个数据服务实例，避免数据不一致

    管理整个应用程序的数据存取，包括：
    - 项目列表（projects）
    - 流程阶段列表（workflow_stages）

    所有数据以JSON格式存储在本地文件中
    """

    _instance: Optional["DataService"] = None  # 单例实例缓存，全局唯一

    def __new__(cls, data_file_path: str = ""):
        """单例模式：确保全局只有一个实例
        重写 __new__ 方法，首次调用时创建实例并缓存，后续调用返回同一实例
        """
        if cls._instance is None:  # 尚未创建实例
            cls._instance = super().__new__(cls)  # 调用父类object的__new__创建实例
            cls._instance._initialized = False  # 标记实例尚未初始化
        return cls._instance  # 返回缓存的单例实例

    def __init__(self, data_file_path: str = ""):
        """初始化数据服务
        由于单例模式，__init__ 可能被多次调用，通过 _initialized 标志防止重复初始化

        Args:
            data_file_path: 数据文件路径（仅在首次创建时使用）
        """
        if self._initialized:  # 已初始化过，直接返回
            return
        self._initialized = True  # 标记已初始化
        self._data_file_path = data_file_path  # 保存数据文件路径
        self._data: dict = {  # 内存中的数据结构，包含项目和流程阶段两个顶层键
            "projects": [],          # 项目列表（每个元素为字典）
            "workflow_stages": [],   # 流程阶段列表（每个元素为字典）
        }
        self._load()  # 从文件加载数据或初始化默认数据

    # ==================== 文件操作 ====================

    def reload(self):
        """重新从文件加载数据（WebDAV恢复后刷新）"""
        self._load()

    def _load(self):
        """从JSON文件加载数据，文件不存在则使用默认数据"""

        if not self._data_file_path:  # 数据文件路径为空，不执行加载
            return
        if os.path.exists(self._data_file_path):  # 数据文件存在
            try:
                with open(self._data_file_path, 'r', encoding='utf-8') as f:  # 以UTF-8读取文件
                    loaded = json.load(f)  # 解析JSON
                    self._data["projects"] = loaded.get("projects", [])  # 提取项目列表
                    self._data["workflow_stages"] = loaded.get("workflow_stages", [])  # 提取阶段列表
            except (json.JSONDecodeError, IOError):  # 文件损坏或读取错误
                self._init_default_data()  # 回退到默认数据
        else:
            self._init_default_data()  # 文件不存在，初始化默认数据

    def _init_default_data(self):
        """初始化默认数据结构和默认流程阶段
        使用 Config 中定义的 DEFAULT_WORKFLOW_STAGES 作为初始流程，
        项目列表初始为空
        """
        from utils.config import Config  # 延迟导入，避免循环依赖
        self._data["workflow_stages"] = Config.DEFAULT_WORKFLOW_STAGES.copy()  # 复制默认流程阶段（防止修改原列表）
        self._data["projects"] = []  # 初始项目列表为空
        self.save()  # 立即保存到文件

    def save(self):
        """将数据原子写入JSON文件
        采用"先写临时文件，成功后再替换原文件"的策略，防止写入过程中
        程序崩溃或断电导致原数据文件损坏
        """
        if not self._data_file_path:  # 未设置数据文件路径则不保存
            return
        os.makedirs(os.path.dirname(self._data_file_path), exist_ok=True)  # 确保数据目录存在
        try:
            dir_name = os.path.dirname(self._data_file_path)  # 获取数据文件所在目录
            with tempfile.NamedTemporaryFile(  # 创建临时文件（原子写入策略）
                mode='w', encoding='utf-8',     # 文本写入模式，UTF-8编码
                dir=dir_name, delete=False, suffix='.tmp'  # 在同目录下创建，不自动删除，.tmp后缀
            ) as tf:
                json.dump(self._data, tf, ensure_ascii=False, indent=2)  # 将数据写入临时文件
                temp_name = tf.name  # 记录临时文件名
            os.replace(temp_name, self._data_file_path)  # 原子性替换：用临时文件替换原文件
        except IOError:  # 临时文件写入失败（磁盘满、权限不足等）
            # 回退：直接写入（不够原子，但保证数据不丢）
            with open(self._data_file_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ==================== 项目数据操作 ====================

    def get_all_projects(self) -> list[dict]:
        """获取所有项目的字典列表"""
        return self._data.get("projects", [])  # 返回项目列表，不存在则返回空列表

    def get_project_by_id(self, project_id: str) -> Optional[dict]:
        """根据ID查找项目

        Args:
            project_id: 项目唯一标识

        Returns:
            项目字典，未找到返回None
        """
        for proj in self._data.get("projects", []):  # 遍历所有项目
            if proj.get("id") == project_id:  # ID匹配
                return proj  # 返回找到的项目字典
        return None  # 未找到，返回None

    def add_project(self, project_dict: dict):
        """添加新项目到数据中

        Args:
            project_dict: 项目字典数据（通常由 Project.to_dict() 生成）
        """
        if "projects" not in self._data:  # 防御：确保projects键存在
            self._data["projects"] = []
        self._data["projects"].append(project_dict)  # 将新项目追加到列表末尾
        self.save()  # 立即持久化

    def update_project(self, project_id: str, updates: dict):
        """更新指定项目的属性

        Args:
            project_id: 目标项目ID
            updates: 需要更新的字段字典（键为字段名，值为新数据）
        """
        proj = self.get_project_by_id(project_id)  # 查找目标项目
        if proj:  # 项目存在
            proj.update(updates)  # 原地更新项目字典
            self.save()  # 持久化变更

    def delete_project(self, project_id: str) -> bool:
        """删除指定项目

        Args:
            project_id: 要删除的项目ID

        Returns:
            True表示删除成功，False表示未找到该项目
        """
        projects = self._data.get("projects", [])  # 获取项目列表引用
        for i, proj in enumerate(projects):  # 遍历项目列表（带索引）
            if proj.get("id") == project_id:  # 找到匹配ID的项目
                projects.pop(i)  # 按索引删除
                self.save()  # 持久化变更
                return True  # 返回删除成功
        return False  # 未找到匹配的项目

    # ==================== 流程阶段数据操作 ====================

    def get_all_stages(self) -> list[dict]:
        """获取所有流程阶段的字典列表，按order排序"""
        stages = self._data.get("workflow_stages", [])  # 获取阶段列表
        return sorted(stages, key=lambda s: s.get("order", 0))  # 按order字段升序排列

    def add_stage(self, stage_dict: dict):
        """添加新的流程阶段

        Args:
            stage_dict: 阶段字典数据（由 WorkflowStage.to_dict() 生成）
        """
        if "workflow_stages" not in self._data:  # 防御：确保workflow_stages键存在
            self._data["workflow_stages"] = []
        self._data["workflow_stages"].append(stage_dict)  # 追加新阶段
        self.save()  # 立即持久化

    def update_stage(self, stage_id: str, updates: dict):
        """更新指定流程阶段

        Args:
            stage_id: 目标阶段ID
            updates: 需要更新的字段字典
        """
        for stage in self._data.get("workflow_stages", []):  # 遍历所有阶段
            if stage.get("id") == stage_id:  # 找到匹配的阶段
                stage.update(updates)  # 原地更新阶段字段
                self.save()  # 持久化变更
                return  # 找到并更新后退出

    def delete_stage(self, stage_id: str) -> bool:
        """删除指定流程阶段

        Args:
            stage_id: 要删除的阶段ID

        Returns:
            True表示删除成功，False表示未找到该阶段
        """
        stages = self._data.get("workflow_stages", [])  # 获取阶段列表
        for i, stage in enumerate(stages):  # 遍历阶段列表
            if stage.get("id") == stage_id:  # ID匹配
                stages.pop(i)  # 按索引删除
                self.save()  # 持久化变更
                return True  # 返回成功
        return False  # 未找到，返回失败

    def replace_all_stages(self, stages_list: list[dict]):
        """替换全部流程阶段（用于流程重排序和批量更新）

        Args:
            stages_list: 新的阶段列表（完整替换现有列表）
        """
        self._data["workflow_stages"] = stages_list  # 直接替换整个阶段列表
        self.save()  # 立即持久化
