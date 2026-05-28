"""
流程管理服务 - 处理等保测评流程阶段的配置和管理

负责：
- 流程阶段的增删改查
- 阶段排序管理
- 默认流程初始化
- 变更日志记录
"""

from typing import Optional, Callable  # 类型提示：Optional表可空值，Callable表可调用对象
from models.workflow import WorkflowStage  # 导入流程阶段实体类
from services.data_service import DataService  # 导入数据持久化服务
from utils.helpers import generate_id  # 导入ID生成函数（虽然generate_id未在本文件中直接使用，但保留以备用）


class WorkflowService:
    """流程管理服务
    封装所有流程阶段相关的业务逻辑，支持自定义流程配置。
    对流程的所有写操作都会自动记录操作日志。
    """

    def __init__(self, data_service: DataService,
                 log_callback: Optional[Callable] = None):
        """初始化流程管理服务

        Args:
            data_service: 数据持久化服务实例（单例）
            log_callback: 操作日志回调函数，签名为 (action, detail, **kwargs)
        """
        self._ds = data_service  # 持有数据服务引用，用于读写阶段数据
        # 保存日志回调，None时使用空lambda避免后续None检查
        self._log = log_callback or (lambda *a, **kw: None)

    # ==================== 查询操作 ====================

    def get_all_stages(self) -> list[WorkflowStage]:
        """获取所有流程阶段，按order字段排序（从左到右的顺序）"""
        dicts = self._ds.get_all_stages()  # 从数据层获取已排序的阶段字典列表
        return [WorkflowStage.from_dict(d) for d in dicts]  # 将每个字典转换为WorkflowStage对象

    def get_stage_by_id(self, stage_id: str) -> Optional[WorkflowStage]:
        """根据ID获取指定阶段

        Args:
            stage_id: 阶段唯一标识

        Returns:
            WorkflowStage对象，未找到返回None
        """
        for s in self._ds.get_all_stages():  # 遍历所有阶段字典
            if s.get("id") == stage_id:  # ID匹配
                return WorkflowStage.from_dict(s)  # 转换为对象并返回
        return None  # 未找到

    def get_first_stage_id(self) -> str:
        """获取第一个阶段（order最小的）的ID，作为新项目创建时的默认阶段"""
        stages = self.get_all_stages()  # 获取所有阶段（已按order排序）
        return stages[0].id if stages else ""  # 有阶段则返回第一个的ID，否则返回空字符串

    def get_stage_name(self, stage_id: str) -> str:
        """根据阶段ID获取阶段名称，用于显示和日志"""
        stage = self.get_stage_by_id(stage_id)  # 查找阶段对象
        return stage.name if stage else "未知阶段"  # 找到返回名称，否则返回"未知阶段"

    # ==================== 增删改操作 ====================

    def add_stage(self, name: str, color: str = "#3498db") -> tuple[bool, str, Optional[WorkflowStage]]:
        """添加新的流程阶段（自动追加到流程末尾，即order设为最大）

        Args:
            name: 新阶段的显示名称
            color: 新阶段的标识颜色（十六进制颜色码）

        Returns:
            (是否成功, 消息, 新创建的WorkflowStage对象或None)
        """
        if not name or not name.strip():  # 名称为空或全空白
            return False, "阶段名称不能为空", None

        stages = self.get_all_stages()  # 获取现有阶段列表
        max_order = max((s.order for s in stages), default=-1)  # 找到当前最大的order值，空列表时默认为-1

        stage = WorkflowStage(  # 创建新的阶段对象
            name=name.strip(),     # 去除首尾空白后的名称
            order=max_order + 1,   # 排序值为当前最大值+1，即追加到末尾
            color=color,           # 标识颜色
        )
        self._ds.add_stage(stage.to_dict())  # 将阶段对象序列化后添加到数据层

        self._log(  # 记录新增阶段日志
            action="新增阶段",
            detail=f"添加流程阶段「{stage.name}」",
        )
        return True, f"阶段「{stage.name}」已添加", stage  # 返回成功信息和新创建的对象

    def update_stage_width(self, stage_id: str, column_width: int):
        """更新阶段列宽（便捷方法，直接写入数据层）

        Args:
            stage_id: 目标阶段ID
            column_width: 新的列宽值（像素）
        """
        self._ds.update_stage(stage_id, {"column_width": column_width})

    def update_stage(self, stage_id: str, name: str = None,
                     color: str = None) -> tuple[bool, str]:
        """更新阶段信息

        Args:
            stage_id: 目标阶段ID
            name: 新名称（None表示不更新）
            color: 新颜色（None表示不更新）

        Returns:
            (是否成功, 消息)
        """
        stage = self.get_stage_by_id(stage_id)  # 查找阶段
        if not stage:  # 阶段不存在
            return False, "阶段不存在"

        updates = {}  # 构建需要更新的字段字典
        old_name = stage.name  # 保存旧名称用于日志
        if name is not None and name.strip():  # 传入了非空名称
            updates["name"] = name.strip()  # 记录名称更新
        if color is not None:  # 传入了颜色值
            updates["color"] = color  # 记录颜色更新

        if not updates:  # 没有需要更新的字段
            return False, "没有需要更新的内容"

        self._ds.update_stage(stage_id, updates)  # 将更新发送到数据层

        new_name = updates.get("name", old_name)  # 取新名称或保留旧名称
        self._log(  # 记录编辑流程日志
            action="编辑流程",
            detail=f"修改流程阶段「{old_name}」→「{new_name}」",
        )
        return True, "阶段更新成功"

    def delete_stage(self, stage_id: str) -> tuple[bool, str]:
        """删除流程阶段
        删除后自动重新排列剩余阶段的order序号，保持连续

        Args:
            stage_id: 要删除的阶段ID

        Returns:
            (是否成功, 消息)
        """
        stage = self.get_stage_by_id(stage_id)  # 查找要删除的阶段
        if not stage:  # 阶段不存在
            return False, "阶段不存在"

        stages = self.get_all_stages()  # 获取当前所有阶段
        if len(stages) <= 1:  # 只剩一个阶段时不允许删除
            return False, "至少保留一个流程阶段"

        self._ds.delete_stage(stage_id)  # 从数据层删除阶段

        # 重新排列剩余阶段的order，确保order从0开始连续排列
        remaining = self.get_all_stages()  # 获取删除后的剩余阶段
        for i, s in enumerate(remaining):  # 遍历剩余阶段并分配新序号
            self._ds.update_stage(s.id, {"order": i})  # 将order设为当前索引值

        self._log(  # 记录删除阶段日志
            action="删除阶段",
            detail=f"删除流程阶段「{stage.name}」",
        )
        return True, f"阶段「{stage.name}」已删除"

    def reorder_stages(self, stage_ids: list[str]) -> tuple[bool, str]:
        """重新排序流程阶段
        根据传入的阶段ID列表顺序重新分配order值

        Args:
            stage_ids: 按新顺序排列的阶段ID列表

        Returns:
            (是否成功, 消息)
        """
        for i, sid in enumerate(stage_ids):  # 遍历新顺序列表
            self._ds.update_stage(sid, {"order": i})  # 将order设为当前索引值
        self._log(  # 记录重排序日志
            action="编辑流程",
            detail="重新排列流程阶段顺序",
        )
        return True, "阶段顺序已更新"

    def reset_to_default(self) -> tuple[bool, str]:
        """重置为系统默认的流程配置（8个标准等保测评阶段）"""
        from utils.config import Config  # 延迟导入配置，避免循环依赖
        self._ds.replace_all_stages(  # 用默认流程替换全部阶段
            [s.copy() for s in Config.DEFAULT_WORKFLOW_STAGES]  # 深拷贝默认阶段列表，避免修改原配置
        )
        self._log(  # 记录重置日志
            action="编辑流程",
            detail="重置流程为默认配置",
        )
        return True, "流程已重置为默认配置"
