"""
数据持久化服务模块 - 负责所有业务数据的 JSON 文件读写操作。

本模块是系统的数据访问层（Data Access Layer），所有业务服务（ProjectService、
WorkflowService 等）均通过它来完成数据的存取，不直接操作文件系统。

核心设计要点：
1. 单例模式（Singleton）：确保全局只有一个 DataService 实例，
   避免多实例操作同一文件导致的数据不一致问题。
2. 原子写入（Atomic Write）：保存数据时采用"先写临时文件，成功后再替换原文件"
   的策略，防止写入中断（崩溃、断电）导致原数据文件损坏。
3. 默认数据初始化：首次启动或无数据文件时，自动使用 Config 中预定义的
   默认流程阶段初始化数据，确保系统立即可用。
4. 统一数据接口：项目数据和流程阶段数据通过统一的字典列表接口管理，
   上层服务负责将实体对象与字典之间的转换。

数据文件结构（dap_data.json）:
    {
        "projects": [ {...}, {...} ],        // 项目列表
        "workflow_stages": [ {...}, {...} ]  // 流程阶段列表
    }
"""

# ---------------------------------------------------------------------------
# 标准库导入
# ---------------------------------------------------------------------------
import json                  # JSON 序列化/反序列化，用于数据的持久化存储
import os                    # 操作系统接口，用于目录创建和文件存在性检查
import tempfile              # 临时文件模块，用于实现原子写入策略
from typing import Optional  # 类型提示，用于标记可选返回值类型

from services.interfaces import IDataService  # 数据服务抽象接口（DIP）


class DataService(IDataService):
    """数据持久化服务（单例模式）。

    作为系统唯一的数据访问入口，管理内存中的数据结构并提供文件读写功能。
    所有数据读写操作均通过本服务完成，保证数据的一致性。

    管理的顶层数据结构：
    - projects (list[dict]): 项目字典列表，每个字典包含项目的完整字段。
    - workflow_stages (list[dict]): 流程阶段字典列表，按 order 排序。

    属性说明:
        _instance (DataService | None): 类级别的单例缓存，首次创建后在此保存引用。
        _initialized (bool): 实例是否已完成初始化（防止 __init__ 被重复执行）。
        _data_file_path (str): 数据文件的完整路径。
        _data (dict): 内存中的数据字典，包含 projects 和 workflow_stages 两个键。
    """

    _instance: Optional["DataService"] = None  # 类级别单例实例缓存

    # ========================================================================
    # 单例模式实现
    # ========================================================================

    def __new__(cls, data_file_path: str = ""):
        """单例模式 __new__ 方法。

        重写 object.__new__ 实现单例控制：首次调用时创建实例并缓存，
        后续所有调用均返回缓存的同一实例，确保全局只有一个 DataService 对象。

        Args:
            data_file_path: 数据文件路径（仅首次创建实例时生效）。

        Returns:
            DataService: 全局唯一的 DataService 实例。
        """
        if cls._instance is None:
            # 首次调用：调用父类 object.__new__ 创建新实例
            cls._instance = super().__new__(cls)
            # 标记实例尚未完成 __init__ 初始化
            cls._instance._initialized = False
        # 返回缓存的单例实例
        return cls._instance

    def __init__(self, data_file_path: str = ""):
        """初始化数据服务实例。

        由于单例模式下 __init__ 可能被多次调用（每次 DataService() 都会触发），
        通过 _initialized 标志防止重复执行初始化逻辑。

        Args:
            data_file_path: 数据 JSON 文件的完整存储路径。
        """
        if self._initialized:
            # 已初始化，跳过重复初始化（单例模式下 __init__ 会被多次调用）
            return
        self._initialized = True               # 标记为已初始化
        self._data_file_path = data_file_path  # 保存数据文件路径

        # 初始化内存数据结构：projects 和 workflow_stages 两个顶层键
        self._data: dict = {
            "projects": [],          # 项目列表（初始为空，由 _load 填充）
            "workflow_stages": [],   # 流程阶段列表（初始为空，由 _load 填充）
        }
        # 从文件加载已有数据，或初始化默认数据
        self._load()

    # ========================================================================
    # 文件读写操作
    # ========================================================================

    def reload(self):
        """重新从文件加载数据到内存。

        用于以下场景：
        - WebDAV 恢复操作后，需要刷新内存中的数据以反映远程恢复的内容。
        - 外部修改了数据文件，需要重新加载以同步。
        """
        self._load()

    def _load(self):
        """从 JSON 文件加载数据到内存。

        加载逻辑：
        1. 如果数据文件路径为空，跳过加载（服务未正确配置）。
        2. 如果文件存在，读取并解析 JSON，提取 projects 和 workflow_stages。
        3. 如果文件不存在或解析失败，回退到初始化默认数据。
        """
        if not self._data_file_path:
            # 数据文件路径未设置（服务尚未完全初始化），直接返回
            return

        if os.path.exists(self._data_file_path):
            # 数据文件存在：尝试读取和解析
            try:
                with open(self._data_file_path, 'r', encoding='utf-8') as f:
                    raw = f.read()
                    try:
                        from utils.crypto_utils import decrypt_data
                        data_str = decrypt_data(raw)
                    except Exception:
                        data_str = raw
                    loaded = json.loads(data_str)
                    # 提取项目列表并清理历史脏数据(换行/回车/制表符)
                    self._data["projects"] = loaded.get("projects", [])
                    # 清理历史脏数据: 换行符/回车/制表符
                    for p in self._data["projects"]:
                        for f in ("company_name", "system_name"):
                            if f in p and isinstance(p[f], str):
                                p[f] = p[f].replace(chr(10),"").replace(chr(13),"").replace(chr(9),"")
                    self._data["workflow_stages"] = loaded.get("workflow_stages", [])
            except (json.JSONDecodeError, IOError):
                # JSON 格式损坏 或 文件读取错误：回退到默认数据初始化
                self._init_default_data()
        else:
            # 数据文件不存在（首次启动或文件被删除）：初始化默认数据
            self._init_default_data()

    def _init_default_data(self):
        """初始化默认数据结构和默认流程阶段。

        从 Config 类中获取系统预定义的默认流程阶段（8 个标准等保测评阶段），
        项目列表初始化为空。完成后立即保存到文件，确保后续启动时有数据文件可用。
        """
        # 延迟导入 Config 以避免模块级的循环依赖
        from utils.config import Config
        # 使用 copy() 深拷贝默认流程，防止后续修改污染 Config 中的原始定义
        self._data["workflow_stages"] = Config.DEFAULT_WORKFLOW_STAGES.copy()
        # 新系统启动时项目列表为空
        self._data["projects"] = []
        # 立即持久化默认数据到文件
        self.save()

    def save(self):
        """将内存中的全部数据原子写入 JSON 文件。

        原子写入策略（Atomic Write）实现:
        1. 在同目录下创建一个临时文件（.tmp 后缀）。
        2. 将所有数据写入临时文件。
        3. 写入成功后，用 os.replace() 原子性地将临时文件替换到目标路径。

        这种策略的优势：
        - 如果写入过程中程序崩溃或断电，受损的是临时文件而非原始数据文件。
          （下次启动时数据文件完好无损，丢失的只是上一次未完成的写入）
        - os.replace() 是操作系统级别的原子重命名操作，外部进程要么看到旧文件，
          要么看到完整的新文件，不会看到写了一半的中间状态。

        回退机制：
        - 如果临时文件写入失败（如磁盘满、权限不足），回退到直接写目标文件。
        - 回退写法不保证原子性，但至少尽力保存数据（比完全丢弃好）。

        Raises:
            无显式异常 —— 所有 I/O 异常在方法内部捕获并降级处理。
        """
        if not self._data_file_path:
            # 未设置数据文件路径（如测试环境），跳过保存
            return

        # 确保数据文件所在的目录树存在
        os.makedirs(os.path.dirname(self._data_file_path), exist_ok=True)

        try:
            dir_name = os.path.dirname(self._data_file_path)
            # 在同目录下创建临时文件，确保 os.replace 是原子操作（同一文件系统）
            with tempfile.NamedTemporaryFile(
                mode='w',          # 文本写入模式
                encoding='utf-8',  # UTF-8 编码，支持中文内容
                dir=dir_name,      # 在目标目录下创建临时文件（确保同文件系统可用 rename）
                delete=False,      # 不自动删除，后续需手动处理
                suffix='.tmp'      # 临时文件后缀，便于识别
            ) as tf:
                # ensure_ascii=False: 保留中文字符，不转义为 \uXXXX
                # indent=2: 格式化输出，便于人工查看和版本控制 diff
                data_str = json.dumps(self._data, ensure_ascii=False, indent=2)
                from utils.crypto_utils import encrypt_data
                tf.write(encrypt_data(data_str))
                temp_name = tf.name

            os.replace(temp_name, self._data_file_path)

        except IOError:
            with open(self._data_file_path, 'w', encoding='utf-8') as f:
                data_str = json.dumps(self._data, ensure_ascii=False, indent=2)
                from utils.crypto_utils import encrypt_data
                f.write(encrypt_data(data_str))

    # ========================================================================
    # 项目数据操作（CRUD）
    # ========================================================================

    def get_all_projects(self) -> list[dict]:
        """获取所有项目的字典列表。

        Returns:
            list[dict]: 项目字典列表，每个元素为项目的完整字段字典。
                       如果没有项目则返回空列表。
        """
        # 使用 get 防御 projects 键不存在的情况
        return self._data.get("projects", [])

    def get_project_by_id(self, project_id: str) -> Optional[dict]:
        """根据项目ID查找单个项目。

        遍历项目列表线性查找（适合中小规模数据），返回匹配的第一个项目。

        Args:
            project_id: 要查找的项目唯一标识符。

        Returns:
            dict | None: 匹配的项目字典，未找到时返回 None。
        """
        for proj in self._data.get("projects", []):
            if proj.get("id") == project_id:
                # 找到匹配ID的项目，直接返回
                return proj
        # 遍历完毕未找到
        return None

    def add_project(self, project_dict: dict):
        """向数据中添加新项目。

        将项目字典追加到项目列表末尾，并立即持久化到文件。

        Args:
            project_dict: 项目完整字段字典（通常由 Project.to_dict() 生成）。
        """
        # 防御性编程：确保 projects 键存在（理论上始终存在，但防范意外）
        if "projects" not in self._data:
            self._data["projects"] = []
        # 追加到列表末尾
        self._data["projects"].append(project_dict)
        # 立即持久化变更
        self.save()

    def update_project(self, project_id: str, updates: dict):
        """更新指定项目的字段。

        通过 dict.update() 原地更新项目字典，支持部分字段更新。

        Args:
            project_id: 要更新的项目唯一标识符。
            updates: 需要更新的字段字典（键为字段名，值为新内容）。
        """
        proj = self.get_project_by_id(project_id)
        if proj:
            # 项目存在：原地更新字典（修改的是列表中的引用）
            proj.update(updates)
            # 持久化变更
            self.save()

    def delete_project(self, project_id: str) -> bool:
        """删除指定项目。

        按索引从项目列表中移除匹配ID的第一个项目。

        Args:
            project_id: 要删除的项目唯一标识符。

        Returns:
            bool: True 表示删除成功，False 表示未找到匹配的项目。
        """
        projects = self._data.get("projects", [])
        for i, proj in enumerate(projects):
            if proj.get("id") == project_id:
                # 按索引删除（O(1) 的 pop 操作 + O(n) 的后续元素移动）
                projects.pop(i)
                # 持久化变更
                self.save()
                return True
        # 遍历完毕未找到匹配项目
        return False

    # ========================================================================
    # 流程阶段数据操作
    # ========================================================================

    def get_all_stages(self) -> list[dict]:
        """获取所有流程阶段的字典列表，按 order 升序排列。

        Returns:
            list[dict]: 按 order 字段升序排列的阶段字典列表。
        """
        stages = self._data.get("workflow_stages", [])
        # 按 order 字段排序：确保看板列从左到右的正确顺序
        return sorted(stages, key=lambda s: s.get("order", 0))

    def add_stage(self, stage_dict: dict):
        """添加新的流程阶段到数据中。

        将阶段字典追加到阶段列表，并立即持久化。

        Args:
            stage_dict: 阶段完整字段字典（通常由 WorkflowStage.to_dict() 生成）。
        """
        # 防御性编程：确保 workflow_stages 键存在
        if "workflow_stages" not in self._data:
            self._data["workflow_stages"] = []
        # 追加新阶段
        self._data["workflow_stages"].append(stage_dict)
        # 立即持久化变更
        self.save()

    def update_stage(self, stage_id: str, updates: dict):
        """更新指定流程阶段的字段。

        原地更新匹配的阶段字典，支持部分字段更新（如仅修改颜色、名称等）。

        Args:
            stage_id: 要更新的阶段唯一标识符。
            updates: 需要更新的字段字典（键为字段名，值为新内容）。
        """
        for stage in self._data.get("workflow_stages", []):
            if stage.get("id") == stage_id:
                # 找到匹配的阶段：原地更新字典
                stage.update(updates)
                # 持久化变更
                self.save()
                # 找到目标后立即退出循环（ID 理论上是唯一的）
                return

    def delete_stage(self, stage_id: str) -> bool:
        """删除指定流程阶段。

        按索引从阶段列表中移除匹配ID的第一个阶段。

        Args:
            stage_id: 要删除的阶段唯一标识符。

        Returns:
            bool: True 表示删除成功，False 表示未找到匹配的阶段。
        """
        stages = self._data.get("workflow_stages", [])
        for i, stage in enumerate(stages):
            if stage.get("id") == stage_id:
                # 按索引删除匹配阶段
                stages.pop(i)
                # 持久化变更
                self.save()
                return True
        # 未找到匹配阶段
        return False

    def replace_all_stages(self, stages_list: list[dict]):
        """替换全部流程阶段（批量更新操作）。

        用于以下场景：
        - 重置为默认流程配置（reset_to_default）
        - 流程阶段批量重排序后的保存
        - 批量导入流程配置

        Args:
            stages_list: 新的阶段字典列表，完全替换现有的 workflow_stages。
        """
        # 直接替换整个阶段列表引用
        self._data["workflow_stages"] = stages_list
        # 立即持久化变更
        self.save()
