"""
公共 UI 组件模块 — 跨对话框复用的 Tkinter 布局工具

本模块提供项目中多个对话框共用的布局组件和工具函数，
消除跨文件重复代码（原则 #1 分层与模块化）。

提供的组件：
  - center_window(window): 将窗口相对于父窗口居中
  - make_button_bar(parent, buttons): 创建灰底分割线 + 按钮容器
  - make_scrollable(parent): 创建 Canvas + Scrollbar 滚动容器
"""

import tkinter as tk
from tkinter import ttk


# ===========================================================================
# 窗口居中
# ===========================================================================

def center_window(window: tk.Toplevel) -> None:
    """将 Toplevel 对话框相对于其父窗口居中显示。

    调用 update_idletasks() 确保组件尺寸计算完成后再计算居中位置。

    Args:
        window: 需要居中的 Toplevel 实例。
    """
    window.update_idletasks()
    w = window.winfo_width()
    h = window.winfo_height()
    pw = window.master.winfo_width()
    ph = window.master.winfo_height()
    px = window.master.winfo_rootx()
    py = window.master.winfo_rooty()
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2
    window.geometry(f"+{x}+{y}")


# ===========================================================================
# 底部按钮栏
# ===========================================================================

def make_button_bar(parent: tk.Frame, bg: str = "#f0f2f5",
                    divider_color: str = "#d0d5dd") -> tk.Frame:
    """创建底部按钮栏的标准布局：灰底容器 + 顶部分割线 + 按钮区。

    项目中 7+ 个对话框使用相同模式：
      Frame(bg=bg)
        ├── Frame(bg=divider_color, height=1)   ← 1px 分割线
        └── Frame(bg=bg)                         ← 按钮容器

    Args:
        parent: 父级容器（通常是对话框主 Frame）。
        bg: 按钮栏背景色。
        divider_color: 分割线颜色。

    Returns:
        tk.Frame: 内层按钮容器（直接 pack buttons 到此 Frame）。
    """
    btn_frame = tk.Frame(parent, bg=bg)
    btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

    tk.Frame(btn_frame, bg=divider_color, height=1).pack(fill=tk.X)

    inner = tk.Frame(btn_frame, bg=bg)
    inner.pack(fill=tk.X, padx=16, pady=8)
    return inner


# ===========================================================================
# 滚动容器
# ===========================================================================

def make_scrollable(parent: tk.Frame, bg: str = "#ffffff") -> tuple[tk.Canvas, tk.Frame]:
    """创建带垂直滚动条的 Canvas 滚动容器。

    用于内容可能溢出窗口高度的对话框（如流程编辑、报告打印）。

    Args:
        parent: 父级容器。
        bg: 背景色。

    Returns:
        tuple[tk.Canvas, tk.Frame]: (画布, 可滚动内容Frame)。
    """
    canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg=bg)

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    return canvas, scroll_frame
