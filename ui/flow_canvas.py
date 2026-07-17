"""
流程图画布模块 -- 等保测评进度管理系统

以拖拽节点+子节点的拓扑图方式展示项目流程，
替代原有看板列表式布局。

设计原则 #5（技术隔离）：Canvas 绘图细节封装在本模块内。
"""
from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.project import Project
    from models.workflow import WorkflowStage


class FlowCanvas(tk.Frame):
    """流程图画布：阶段节点 + 项目子节点 + 贝塞尔连线 + 拖拽移动。

    用法:
        canvas = FlowCanvas(parent)
        canvas.load(stages, projects)
        canvas.bind_callbacks(on_click, on_double, on_move)
    """

    NODE_W = 130          # 阶段节点宽度
    NODE_H = 48           # 阶段节点高度
    SUBNODE_W = 140       # 子节点宽度
    SUBNODE_H = 28        # 子节点高度
    H_GAP = 60            # 节点水平间距
    V_GAP = 80            # 节点垂直间距
    SUBNODE_V_GAP = 6     # 子节点垂直间距

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#f5f6fa", **kwargs)
        self._canvas = tk.Canvas(self, bg="#f5f6fa", highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # 数据
        self._stages: list[WorkflowStage] = []
        self._projects: list[Project] = []

        # 节点数据: {stage_id: {"node": canvas_id, "label": canvas_id, "count": int, "x": int, "y": int}}
        self._nodes = {}
        # 子节点: [(canvas_id, project_id), ...]
        self._subnodes = []
        # 连线 ID 列表
        self._lines = []
        # 回调
        self.on_node_click = None       # (stage_id)
        self.on_subnode_click = None    # (project_id)
        self.on_subnode_double = None   # (project_id)
        self.on_subnode_move = None     # (project_id, target_stage_id)

        # 拖拽状态
        self._drag_data = {"node": None, "x": 0, "y": 0}

        # 缩放平移
        self._scale = 1.0
        self._offset_x = 0
        self._offset_y = 0

        self._bind_events()

    # =========================================================================
    # 事件绑定
    # =========================================================================

    def _bind_events(self):
        """绑定鼠标交互事件。"""
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Double-Button-1>", self._on_double_click)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_drop)
        self._canvas.bind("<MouseWheel>", self._on_zoom)
        self.bind("<Configure>", self._on_resize)

    def bind_callbacks(self, on_node_click=None, on_subnode_click=None,
                       on_subnode_double=None, on_subnode_move=None):
        """设置外部回调。"""
        self.on_node_click = on_node_click
        self.on_subnode_click = on_subnode_click
        self.on_subnode_double = on_subnode_double
        self.on_subnode_move = on_subnode_move

    # =========================================================================
    # 数据加载与布局
    # =========================================================================

    def load(self, stages: list[WorkflowStage], projects: list[Project]):
        """加载阶段和项目数据并自动布局。多系统按公司合并为一张卡片。"""
        self._stages = stages
        self._projects = projects

        # 按(公司名, 阶段ID)合并项目（与看板逻辑一致）
        from collections import defaultdict
        groups = defaultdict(list)
        for p in projects:
            key = (p.company_name.strip() or "未命名", p.stage_id)
            groups[key].append(p)
        self._merged = list(groups.values())
        self._auto_layout()

    def _auto_layout(self):
        """自动布局算法 — 蛇形排列（每行 4 个节点）。"""
        self._canvas.delete("all")
        self._nodes.clear()
        self._subnodes.clear()
        self._lines.clear()

        COLS = 4
        canvas_w = self.winfo_width() or 1200

        for i, stage in enumerate(self._stages):
            col = i % COLS
            row = i // COLS
            x = 60 + col * (self.NODE_W + self.H_GAP)
            y = 40 + row * (self.NODE_H + self.V_GAP + 60)

            # 绘制阶段节点
            color = stage.color or "#3498db"
            node_id = self._draw_rounded_rect(x, y, self.NODE_W, self.NODE_H,
                                              fill=color, outline=color)

            # 阶段名称标签
            label_id = self._canvas.create_text(
                x + self.NODE_W // 2, y + self.NODE_H // 2 - 6,
                text=stage.name, fill="white",
                font=("Microsoft YaHei", 10, "bold"), anchor="center",
            )

            # 项目计数（合并后）
            merged_count = sum(1 for g in self._merged if g[0].stage_id == stage.id)
            count_id = self._canvas.create_text(
                x + self.NODE_W // 2, y + self.NODE_H // 2 + 12,
                text=str(merged_count), fill="rgba(255,255,255,0.7)",
                font=("Microsoft YaHei", 9), anchor="center",
            )

            self._nodes[stage.id] = {
                "node": node_id, "label": label_id, "count": count_id,
                "x": x, "y": y, "stage": stage,
            }

            # 绘制合并后的子节点
            sub_y = y + self.NODE_H + self.SUBNODE_V_GAP + 10
            merged_groups = [g for g in self._merged if g[0].stage_id == stage.id]

            for j, group in enumerate(merged_groups[:8]):
                sx = x + (self.SUBNODE_W - self.NODE_W) // 2
                sy = sub_y + j * (self.SUBNODE_H + self.SUBNODE_V_GAP)

                first = group[0]
                is_multi = len(group) > 1
                # 标题：多系统→公司名，单系统→系统名
                title = first.company_name if is_multi else (first.system_name or first.company_name or "-")
                if len(title) > 12:
                    title = title[:11] + "…"

                # 子节点高度自适应（多系统时加高以容纳系统列表）
                sn_h = self.SUBNODE_H + (len(group) - 1) * 14 if is_multi else self.SUBNODE_H

                sn_id = self._draw_rounded_rect(
                    sx, sy, self.SUBNODE_W, sn_h,
                    fill="white", outline="#d0d5dd",
                )

                # 状态色条（取最紧急的状态）
                bar_color = self._get_status_color(first)
                for p in group:
                    c = self._get_status_color(p)
                    if c == "#ff0000":
                        bar_color = c
                        break
                    if c == "#ffc000" and bar_color != "#ff0000":
                        bar_color = c
                bar_id = self._canvas.create_rectangle(
                    sx, sy, sx + 6, sy + sn_h,
                    fill=bar_color, outline="",
                )

                # 主标题
                name_id = self._canvas.create_text(
                    sx + 36, sy + 12,
                    text=title, fill="#2c3e50",
                    font=("Microsoft YaHei", 8, "bold"), anchor="w",
                )

                # 多系统时列出子系统名
                sys_ids = []
                if is_multi:
                    sys_text = " | ".join(
                        (p.system_name or "")[:6] for p in group[:5]
                    )
                    if len(sys_text) > 24:
                        sys_text = sys_text[:23] + "…"
                    tid = self._canvas.create_text(
                        sx + 36, sy + 24,
                        text=sys_text, fill="#7f8c8d",
                        font=("Microsoft YaHei", 7), anchor="w",
                    )
                    sys_ids.append(tid)

                self._subnodes.append({
                    "bg": sn_id, "bar": bar_id, "label": name_id,
                    "sys_labels": sys_ids,
                    "project_id": first.id, "stage_id": stage.id,
                    "all_ids": [p.id for p in group],
                    "x": sx, "y": sy,
                })

            # 超过 8 个显示省略
            if len(merged_groups) > 8:
                more_id = self._canvas.create_text(
                    x + self.NODE_W // 2,
                    sub_y + 8 * (self.SUBNODE_H + self.SUBNODE_V_GAP + 10),
                    text=f"+{len(merged_groups) - 8} 更多",
                    fill="#95a5a6", font=("Microsoft YaHei", 8), anchor="center",
                )
                self._subnodes.append({
                    "bg": more_id, "bar": None, "label": more_id,
                    "sys_labels": [], "project_id": None,
                    "all_ids": [], "stage_id": stage.id,
                    "x": x, "y": sub_y + 8 * (self.SUBNODE_H + self.SUBNODE_V_GAP),
                })

        # 绘制阶段间连线
        for i in range(len(self._stages) - 1):
            s1, s2 = self._stages[i], self._stages[i + 1]
            n1, n2 = self._nodes[s1.id], self._nodes[s2.id]
            x1, y1 = n1["x"] + self.NODE_W, n1["y"] + self.NODE_H // 2
            x2, y2 = n2["x"], n2["y"] + self.NODE_H // 2
            line_id = self._draw_arrow(x1, y1, x2, y2)
            self._lines.append(line_id)

        # 更新滚动区域
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    # =========================================================================
    # 绘图工具
    # =========================================================================

    def _draw_rounded_rect(self, x, y, w, h, fill, outline, radius=10):
        """绘制圆角矩形。"""
        coords = (x + radius, y, x + w - radius, y, x + w, y, x + w, y + radius,
                  x + w, y + h - radius, x + w, y + h, x + w - radius, y + h,
                  x + radius, y + h, x, y + h, x, y + h - radius,
                  x, y + radius, x, y)
        return self._canvas.create_polygon(coords, fill=fill, outline=outline,
                                           smooth=True, width=1)

    def _draw_arrow(self, x1, y1, x2, y2):
        """绘制贝塞尔箭头线。"""
        cx = (x1 + x2) // 2
        line = self._canvas.create_line(
            x1, y1, cx, y1, cx, y2, x2, y2,
            smooth=True, fill="#b0b8c1", width=2,
            arrow=tk.LAST, arrowshape=(8, 10, 3),
        )
        return line

    def _get_status_color(self, project: Project) -> str:
        """获取项目状态色（利用已有的 5 色系统）。"""
        from utils.config import Config as Cfg
        if not project.deadline:
            return Cfg.STATUS_COLORS["inactive"]
        from datetime import date
        try:
            dl = date.fromisoformat(project.deadline)
            days = (dl - date.today()).days
        except (ValueError, TypeError):
            return Cfg.STATUS_COLORS["inactive"]
        if days < 0:
            return Cfg.STATUS_COLORS["overdue"]
        elif days <= Cfg.DEADLINE_WARNING_DAYS:
            return Cfg.STATUS_COLORS["warning"]
        return Cfg.STATUS_COLORS["normal"]

    # =========================================================================
    # 交互事件
    # =========================================================================

    def _on_click(self, event):
        """单击事件：分发到节点或子节点。"""
        mx, my = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)

        # 检查子节点
        for sn in self._subnodes:
            if sn.get("project_id") is None:
                continue
            if sn["x"] <= mx <= sn["x"] + self.SUBNODE_W and \
               sn["y"] <= my <= sn["y"] + self.SUBNODE_H:
                if self.on_subnode_click:
                    self.on_subnode_click(sn["project_id"])
                return

        # 检查阶段节点
        for sid, nd in self._nodes.items():
            if nd["x"] <= mx <= nd["x"] + self.NODE_W and \
               nd["y"] <= my <= nd["y"] + self.NODE_H:
                if self.on_node_click:
                    self.on_node_click(sid)
                self._drag_data["node"] = sid
                self._drag_data["x"] = event.x
                self._drag_data["y"] = event.y
                return

    def _on_double_click(self, event):
        """双击子节点 → 打开详情。"""
        mx, my = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        for sn in self._subnodes:
            if sn.get("project_id") is None:
                continue
            if sn["x"] <= mx <= sn["x"] + self.SUBNODE_W and \
               sn["y"] <= my <= sn["y"] + self.SUBNODE_H:
                if self.on_subnode_double:
                    self.on_subnode_double(sn["project_id"])
                return

    def _on_drag(self, event):
        """拖拽移动阶段节点。"""
        sid = self._drag_data.get("node")
        if sid is None:
            return
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        nd = self._nodes[sid]
        nd["x"] += dx
        nd["y"] += dy
        self._canvas.move(nd["node"], dx, dy)
        self._canvas.move(nd["label"], dx, dy)
        self._canvas.move(nd["count"], dx, dy)
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drop(self, event):
        """释放拖拽：检查是否拖到其他阶段上（用于移动项目）。"""
        self._drag_data["node"] = None

    def _on_zoom(self, event):
        """滚轮缩放。"""
        if event.delta > 0:
            self._canvas.scale("all", event.x, event.y, 1.1, 1.1)
        else:
            self._canvas.scale("all", event.x, event.y, 0.9, 0.9)

    def _on_resize(self, event):
        """窗口大小变化时更新滚动区域。"""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
