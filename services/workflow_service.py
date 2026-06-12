"""
流程管理服务模块 - 处理等保测评流程阶段（看板列）的配置和管理。

本模块在 DataService 之上封装流程阶段相关的业务逻辑，负责：
- 流程阶段的增删改查（CRUD）操作
- 阶段排序管理（拖拽重排序、删除后自动重新编号）
- 阶段列宽管理
- 默认流程配置初始化与重置
- 变更操作日志记录（通过回调函数委托给 LogService）

等保测评的标准流程包含 8 个阶段（由 Config.DEFAULT_WORKFLOW_STAGES 定义）：
项目启动 / 现状调研 / 差距评估 / 安全测评 / 整改加固 /
复测验证 / 报告编制 / 项目归档

用户可以自定义添加、删除、重命名和重排序这些阶段。
"""

# ---------------------------------------------------------------------------
# 标准库导入
# ---------------------------------------------------------------------------
from typing import Callable, Optional
# Callable: 用于标注回调函数的类型签名
# Optional: 用于标记可空返回值类型

# ---------------------------------------------------------------------------
# 项目内导入（模型层 + 数据层 + 工具层）
# ---------------------------------------------------------------------------
from models.workflow import WorkflowStage
# 流程阶段实体类，封装阶段的属性和序列化/反序列化逻辑

from services.data_service import DataService
# 数据持久化服务（单例），提供底层 JSON 文件的读写操作

from utils.helpers import generate_id
# 生成唯一ID的工具函数（虽然本文件不直接使用 generate_id，
# 但保留导入以备 WorkflowStage 构造函数需要回退时使用）


class WorkflowService:
    """流程管理服务。

    封装所有流程阶段（看板列）相关的业务逻辑。对流程阶段的所有写操作
    （增、删、改、重排序、重置）都会自动记录操作日志。

    等保测评标准流程的 8 个阶段（由 Config.DEFAULT_WORKFLOW_STAGES 定义）：
    项目启动 -> 现状调研 -> 差距评估 -> 安全测评 -> 整改加固 ->
    复测验证 -> 报告编制 -> 项目归档

    流程阶段的 order 字段从 0 开始连续编号，决定看板列从左到右的排列顺序。
    删除或重排序后会自动重新编号保持连续。

    属性说明:
        _ds (DataService): 数据持久化服务引用（单例），用于底层数据读写。
        _log (Callable): 日志回调函数，签名为 (action, detail, **kwargs)，
                         实际指向 LogService.create_log_callback() 的返回值。
    """

    def __init__(self, data_service: DataService,
                 log_callback: Optional[Callable[..., None]] = None):
        """初始化流程管理服务。

        Args:
            data_service: DataService 的单例实例，提供数据存取能力。
            log_callback: 操作日志回调函数，签名为 (action, detail, **kwargs)。
                          为 None 时使用空操作函数占位，不记录日志。
        """
        # 持有数据层引用，所有阶段数据的读写都委托给它
        self._ds = data_service
        # 日志回调：None 时使用空 lambda 避免每次调用前的 None 检查
        self._log = log_callback or (lambda *a, **kw: None)

    # ========================================================================
    # 查询操作
    # ========================================================================

    def get_all_stages(self) -> list[WorkflowStage]:
        """获取所有流程阶段对象列表。

        从数据层获取已按 order 排序的阶段字典列表，然后转换为 WorkflowStage
        实体对象，排序结果直接来自 DataService.get_all_stages()。

        Returns:
            list[WorkflowStage]: 按 order 升序排列的阶段对象列表。
        """
        # 从数据层获取已排序的字典列表
        dicts = self._ds.get_all_stages()
        # 将每个字典转换为 WorkflowStage 实体对象
        return [WorkflowStage.from_dict(d) for d in dicts]

    def get_stage_by_id(self, stage_id: str) -> Optional[WorkflowStage]:
        """根据阶段ID获取单个阶段对象。

        遍历数据层中的所有阶段字典，查找ID匹配的阶段。

        Args:
            stage_id: 流程阶段的唯一标识符。

        Returns:
            WorkflowStage | None: 匹配的阶段对象，未找到时返回 None。
        """
        for s in self._ds.get_all_stages():
            if s.get("id") == stage_id:
                # 找到匹配的阶段：反序列化为对象并返回
                return WorkflowStage.from_dict(s)
        # 遍历完毕未找到匹配阶段
        return None

    def get_first_stage_id(self) -> str:
        """获取第一个阶段的ID（order 最小的阶段）。

        用于设置新创建项目的默认初始阶段。新项目创建时自动分配到此阶段。

        Returns:
            str: 第一个阶段的ID，如果没有任何阶段则返回空字符串。
        """
        stages = self.get_all_stages()
        # 安全取值：有阶段返回第一个的ID，空列表返回空字符串
        return stages[0].id if stages else ""

    def get_stage_name(self, stage_id: str) -> str:
        """根据阶段ID获取阶段的可读名称。

        与 ProjectService._get_stage_name 类似，但使用 WorkflowStage 对象
        而非直接操作字典，提供更语义化的查询。

        Args:
            stage_id: 流程阶段唯一标识符。

        Returns:
            str: 阶段的显示名称，未找到时返回"未知阶段"。
        """
        stage = self.get_stage_by_id(stage_id)
        return stage.name if stage else "未知阶段"

    # ========================================================================
    # 增删改操作
    # ========================================================================

    def add_stage(self, name: str, color: str = "#3498db") -> tuple[bool, str, Optional[WorkflowStage]]:
        """添加新的流程阶段。

        新阶段自动追加到流程末尾（order 设为当前最大值 + 1），
        这样新增的阶段自动出现在看板的最右侧。

        Args:
            name: 新阶段的显示名称（将展示在看板列标题上）。
            color: 新阶段的标识颜色，十六进制颜色码，默认蓝色。

        Returns:
            tuple[bool, str, WorkflowStage | None]:
                - bool: 操作是否成功。
                - str: 成功/失败的描述消息。
                - WorkflowStage | None: 成功时返回新创建的对象，失败时为 None。
        """
        # 校验：阶段名称不能为空或全空白
        if not name or not name.strip():
            return False, "阶段名称不能为空", None

        # 获取现有阶段列表，计算当前最大的 order 值
        stages = self.get_all_stages()
        # 使用生成器表达式提取所有阶段的 order 值
        # max() 的 default=-1: 空列表时返回 -1，因此新阶段 order = -1 + 1 = 0
        # 这确保了在任何情况下（包括首次添加阶段）order 都从 0 开始
        max_order = max((s.order for s in stages), default=-1)

        # 创建新阶段对象：order 为最大值 + 1（追加到末尾）
        stage = WorkflowStage(
            name=name.strip(),      # 去除首尾空白后的名称
            order=max_order + 1,    # 排在最后的位置
            color=color,            # 用户指定的颜色或默认蓝色
        )

        # 写入数据层
        self._ds.add_stage(stage.to_dict())

        # 记录新增阶段日志
        self._log(
            action="新增阶段",
            detail=f"添加流程阶段「{stage.name}」",
        )

        return True, f"阶段「{stage.name}」已添加", stage

    def update_stage_width(self, stage_id: str, column_width: int):
        """更新阶段的列宽（便捷方法）。

        用户在看板中拖拽调整列宽时调用此方法直接保存列宽值。
        这是一个轻量级的便捷方法，直接写入数据层而不经过完整的 update_stage 流程。

        Args:
            stage_id: 目标阶段唯一标识符。
            column_width: 新的列宽值（像素单位）。
        """
        # 直接向数据层发送列宽更新
        self._ds.update_stage(stage_id, {"column_width": column_width})

    def update_stage(self, stage_id: str,
                     name: Optional[str] = None,
                     color: Optional[str] = None) -> tuple[bool, str]:
        """更新阶段的基本信息（名称和/或颜色）。

        支持部分更新：只传入需要修改的字段，未传入的字段保持不变。

        Args:
            stage_id: 要更新的阶段唯一标识符。
            name: 新的阶段名称（None 表示不修改）。
            color: 新的标识颜色（None 表示不修改）。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        # 先确认阶段存在
        stage = self.get_stage_by_id(stage_id)
        if not stage:
            return False, "阶段不存在"

        # 构建更新字段字典（只包含需要变更的字段）
        updates = {}
        old_name = stage.name  # 保存旧名称，用于日志描述

        if name is not None and name.strip():
            # 传入了有效的新名称
            updates["name"] = name.strip()
        if color is not None:
            # 传入了新颜色
            updates["color"] = color

        if not updates:
            # 没有需要修改的字段
            return False, "没有需要更新的内容"

        # 将更新写入数据层
        self._ds.update_stage(stage_id, updates)

        # 记录编辑流程日志（展示旧名到新名的变化）
        new_name = updates.get("name", old_name)
        self._log(
            action="编辑流程",
            detail=f"修改流程阶段「{old_name}」/「{new_name}」",
        )

        return True, "阶段更新成功"

    def delete_stage(self, stage_id: str) -> tuple[bool, str]:
        """删除指定流程阶段。

        删除后自动重新排列剩余阶段的 order 序号，确保序号从 0 开始连续排列，
        避免序号空洞影响看板列排序。

        安全约束：至少保留一个流程阶段，不允许删除最后一个。

        Args:
            stage_id: 要删除的阶段唯一标识符。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        # 先确认阶段存在
        stage = self.get_stage_by_id(stage_id)
        if not stage:
            return False, "阶段不存在"

        # 安全约束：至少保留一个阶段
        stages = self.get_all_stages()
        if len(stages) <= 1:
            return False, "至少保留一个流程阶段"

        # 从数据层删除指定阶段
        self._ds.delete_stage(stage_id)

        # 删除后重新排列剩余阶段的 order，确保 0, 1, 2, ... 连续排列
        # 不重置的话会出现例如 [0, 2, 3] 的情况（order 1 缺失），看板列有空洞
        remaining = self.get_all_stages()
        for i, s in enumerate(remaining):
            # 将第 i 个阶段的 order 设为 i（紧凑连续排列）
            # 例如删除 order=1 的阶段后，原先 order=2 的阶段变为 order=1
            self._ds.update_stage(s.id, {"order": i})

        # 记录删除阶段日志
        self._log(
            action="删除阶段",
            detail=f"删除流程阶段「{stage.name}」",
        )

        return True, f"阶段「{stage.name}」已删除"

    def reorder_stages(self, stage_ids: list[str]) -> tuple[bool, str]:
        """重新排序流程阶段（看板列拖拽排序）。

        根据传入的阶段ID列表的顺序，依次为每个阶段分配新的 order 值。
        stage_ids[0] 的 order 设为 0，stage_ids[1] 的 order 设为 1，依此类推。

        Args:
            stage_ids: 按新顺序排列的阶段ID列表。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        for i, sid in enumerate(stage_ids):
            # 按列表中的位置分配 order 值：第 0 个 = order 0
            self._ds.update_stage(sid, {"order": i})

        # 记录重排序日志
        self._log(
            action="编辑流程",
            detail="重新排列流程阶段顺序",
        )

        return True, "阶段顺序已更新"

    def reset_to_default(self) -> tuple[bool, str]:
        """重置为系统默认的流程配置。

        将当前所有流程阶段替换为 Config 中定义的 8 个标准等保测评阶段。
        此操作会删除所有用户自定义的阶段，恢复为出厂默认配置。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        # 延迟导入 Config，避免模块级的循环依赖问题
        from utils.config import Config
        # 使用 .copy() 深拷贝默认阶段列表，防止后续修改污染 Config 中的原始定义
        self._ds.replace_all_stages(
            [s.copy() for s in Config.DEFAULT_WORKFLOW_STAGES]
        )

        # 记录重置日志
        self._log(
            action="编辑流程",
            detail="重置流程为默认配置",
        )

        return True, "流程已重置为默认配置"
