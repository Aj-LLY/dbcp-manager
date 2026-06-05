"""
工具提示模块 - 简易鼠标悬浮提示组件（tooltip）

提供两个主要组件：
  1. _ToolTip 类 - 简易按钮悬浮提示，鼠标悬停时在按钮上方显示文字提示气泡
  2. add_tooltip 函数 - 快捷创建工具提示的便捷封装

使用示例：
  from utils.tooltip import add_tooltip
  add_tooltip(my_button, "这是一条提示信息")
"""

import tkinter as tk  # Python 标准 GUI 库，提供 Label、Toplevel 等组件


# =============================================================================
# _ToolTip 类 - 简易按钮悬浮提示组件
# =============================================================================

class _ToolTip:
    """简易按钮悬浮提示 - 鼠标悬停时在按钮上方显示文字提示气泡

    工作原理：
      1. 绑定 <Enter> 事件：创建无边框 Toplevel 窗口，显示提示文字
      2. 绑定 <Leave> 事件：销毁 Toplevel 窗口，移除提示

    使用示例：
      _ToolTip(my_button, "这是一条提示信息")

    Attributes:
        widget (tk.Widget): 被绑定提示的 Tkinter 组件
        text (str): 要显示的提示文字
        tw (tk.Toplevel | None): 提示气泡窗口实例（显示时创建，离开时销毁）
    """

    def __init__(self, widget, text):
        """初始化工具提示并自动绑定事件

        在传入的 widget 上绑定鼠标进入和离开事件，
        用户无需手动管理事件绑定。

        Args:
            widget: 需要显示提示的 Tkinter 组件（如 Button、Label 等）
            text: 鼠标悬停时显示的提示文字
        """
        self.widget = widget  # 保存目标组件引用
        self.text = text  # 保存提示文字
        self.tw = None  # 提示气泡 Toplevel 窗口引用（开始时为 None）
        widget.bind("<Enter>", self._enter)  # 鼠标进入目标组件 -> 显示提示
        widget.bind("<Leave>", self._leave)  # 鼠标离开目标组件 -> 隐藏提示

    def _enter(self, event=None):
        """鼠标进入事件：创建并显示提示气泡窗口

        气泡窗口定位在目标组件的下方约 22px 处，右偏移 5px，
        使用深色背景（#333）+ 白色文字的样式。

        Args:
            event: Tkinter 的 Enter 事件对象（可选）
        """
        # 计算气泡显示位置（相对于屏幕坐标）
        x, y = self.widget.winfo_rootx() + 5, self.widget.winfo_rooty() + 22  # 目标组件左上角 + 偏移
        self.tw = tk.Toplevel(self.widget)  # 创建新的顶级窗口（独立于主窗口）
        self.tw.wm_overrideredirect(True)  # 去除窗口装饰（标题栏、边框），仅显示内容
        self.tw.wm_geometry(f"+{x}+{y}")  # 设置气泡窗口的屏幕位置
        label = tk.Label(self.tw, text=self.text, bg="#333", fg="white",  # 深灰背景，白色文字
                         font=("Microsoft YaHei", 8), padx=4, pady=1)  # 小号字体，紧凑内边距
        label.pack()  # 打包标签到气泡窗口

    def _leave(self, event=None):
        """鼠标离开事件：销毁提示气泡窗口

        Args:
            event: Tkinter 的 Leave 事件对象（可选）
        """
        if self.tw:  # 如果气泡窗口存在
            self.tw.destroy()  # 销毁窗口并释放资源
            self.tw = None  # 清空引用，避免重复销毁


# =============================================================================
# add_tooltip 函数 - 快捷创建工具提示（公开接口）
# =============================================================================

def add_tooltip(widget, text):
    """为指定组件快速添加鼠标悬浮提示

    这是 _ToolTip 类的便捷封装函数，一行代码即可完成提示绑定。

    Args:
        widget: 需要添加提示的 Tkinter 组件
        text: 悬浮时显示的提示文字
    """
    _ToolTip(widget, text)  # 创建 _ToolTip 实例（自动绑定事件）
