"""
流程图画布模块 -- 等保测评进度管理系统

以拖拽节点+子节点的拓扑图方式展示项目流程。
"""
from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.project import Project
    from models.workflow import WorkflowStage


class FlowCanvas(tk.Frame):
    """流程图画布：阶段节点 + 项目子节点 + 连线 + 拖拽。"""

    NODE_W = 130
    NODE_H = 48
    SUBNODE_W = 140
    SUBNODE_H = 28
    H_GAP = 60
    V_GAP = 80
    SUBNODE_V_GAP = 6

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#f5f6fa", **kwargs)
        self._canvas = tk.Canvas(self, bg="#f5f6fa", highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._stages = []
        self._merged = []
        self._nodes = {}
        self._subnodes = []
        self._lines = []
        self.on_node_click = None
        self.on_subnode_click = None
        self.on_subnode_double = None
        self.on_subnode_move = None
        self._drag_data = {"node": None, "x": 0, "y": 0}
        self._bind_events()

    def _bind_events(self):
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Double-Button-1>", self._on_double_click)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_drop)
        self._canvas.bind("<MouseWheel>", self._on_zoom)
        self.bind("<Configure>", self._on_resize)

    def bind_callbacks(self, on_node_click=None, on_subnode_click=None,
                       on_subnode_double=None, on_subnode_move=None):
        self.on_node_click = on_node_click
        self.on_subnode_click = on_subnode_click
        self.on_subnode_double = on_subnode_double
        self.on_subnode_move = on_subnode_move

    def load(self, stages, projects):
        self._stages = stages
        from collections import defaultdict
        groups = defaultdict(list)
        for p in projects:
            key = (p.company_name.strip() or "未命名", p.stage_id)
            groups[key].append(p)
        self._merged = list(groups.values())
        self.update_idletasks()
        try:
            self._auto_layout()
        except Exception as e:
            import traceback
            print(f"[流程图] 渲染异常: {e}", flush=True)
            traceback.print_exc()

    def _auto_layout(self):
        self._canvas.delete("all")
        self._nodes.clear()
        self._subnodes.clear()
        self._lines.clear()
        if not self._stages:
            return

        COLS = 4
        for i, stage in enumerate(self._stages):
            col = i % COLS
            row = i // COLS
            x = 60 + col * (self.NODE_W + self.H_GAP)
            y = 40 + row * (self.NODE_H + self.V_GAP + 80)

            color = stage.color or "#3498db"
            node_id = self._draw_rounded_rect(
                x, y, self.NODE_W, self.NODE_H, fill=color, outline=color)
            label_id = self._canvas.create_text(
                x + self.NODE_W // 2, y + self.NODE_H // 2 - 6,
                text=stage.name, fill="white",
                font=("Microsoft YaHei", 10, "bold"), anchor="center")
            cnt = sum(1 for g in self._merged if g[0].stage_id == stage.id)
            count_id = self._canvas.create_text(
                x + self.NODE_W // 2, y + self.NODE_H // 2 + 12,
                text=str(cnt), fill="rgba(255,255,255,0.7)",
                font=("Microsoft YaHei", 9), anchor="center")
            self._nodes[stage.id] = {
                "node": node_id, "label": label_id, "count": count_id,
                "x": x, "y": y}

            sub_y = y + self.NODE_H + 10
            m_groups = [g for g in self._merged if g[0].stage_id == stage.id]
            for j, group in enumerate(m_groups[:8]):
                sx = x + (self.SUBNODE_W - self.NODE_W) // 2
                sy = sub_y + j * (self.SUBNODE_H + self.SUBNODE_V_GAP)
                first = group[0]
                is_multi = len(group) > 1
                title = first.company_name if is_multi else (
                    first.system_name or first.company_name or "-")
                if len(title) > 12:
                    title = title[:11] + "…"
                sn_h = self.SUBNODE_H + (len(group) - 1) * 14 if is_multi else self.SUBNODE_H

                sn_id = self._draw_rounded_rect(
                    sx, sy, self.SUBNODE_W, sn_h, fill="white", outline="#d0d5dd")
                bar_color = self._get_status_color(first)
                for p in group:
                    c = self._get_status_color(p)
                    if c == "#ff0000":
                        bar_color = c
                        break
                    if c == "#ffc000" and bar_color != "#ff0000":
                        bar_color = c
                self._canvas.create_rectangle(
                    sx, sy, sx + 6, sy + sn_h, fill=bar_color, outline="")
                self._canvas.create_text(
                    sx + 36, sy + 12, text=title, fill="#2c3e50",
                    font=("Microsoft YaHei", 8, "bold"), anchor="w")
                if is_multi:
                    st = " | ".join((p.system_name or "")[:6] for p in group[:5])
                    if len(st) > 24:
                        st = st[:23] + "…"
                    self._canvas.create_text(
                        sx + 36, sy + 24, text=st, fill="#7f8c8d",
                        font=("Microsoft YaHei", 7), anchor="w")
                self._subnodes.append({
                    "bg": sn_id, "x": sx, "y": sy, "sn_h": sn_h,
                    "project_id": first.id, "all_ids": [p.id for p in group]})

            if len(m_groups) > 8:
                self._canvas.create_text(
                    x + self.NODE_W // 2,
                    sub_y + 8 * (self.SUBNODE_H + self.SUBNODE_V_GAP),
                    text=f"+{len(m_groups) - 8} 更多", fill="#95a5a6",
                    font=("Microsoft YaHei", 8), anchor="center")

        for i in range(len(self._stages) - 1):
            s1, s2 = self._stages[i], self._stages[i + 1]
            n1, n2 = self._nodes[s1.id], self._nodes[s2.id]
            x1, y1 = n1["x"] + self.NODE_W, n1["y"] + self.NODE_H // 2
            x2, y2 = n2["x"], n2["y"] + self.NODE_H // 2
            cx = (x1 + x2) // 2
            self._canvas.create_line(
                x1, y1, cx, y1, cx, y2, x2, y2,
                smooth=True, fill="#b0b8c1", width=2,
                arrow=tk.LAST, arrowshape=(8, 10, 3))
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _draw_rounded_rect(self, x, y, w, h, fill, outline, radius=10):
        coords = (x + radius, y, x + w - radius, y, x + w, y, x + w, y + radius,
                  x + w, y + h - radius, x + w, y + h, x + w - radius, y + h,
                  x + radius, y + h, x, y + h, x, y + h - radius,
                  x, y + radius, x, y)
        return self._canvas.create_polygon(coords, fill=fill, outline=outline,
                                           smooth=True, width=1)

    def _get_status_color(self, project):
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

    def _on_click(self, event):
        mx, my = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        for sn in self._subnodes:
            if sn.get("project_id") is None:
                continue
            h = sn.get("sn_h", self.SUBNODE_H)
            if sn["x"] <= mx <= sn["x"] + self.SUBNODE_W and \
               sn["y"] <= my <= sn["y"] + h:
                if self.on_subnode_click:
                    self.on_subnode_click(sn["project_id"])
                return
        for sid, nd in self._nodes.items():
            if nd["x"] <= mx <= nd["x"] + self.NODE_W and \
               nd["y"] <= my <= nd["y"] + self.NODE_H:
                if self.on_node_click:
                    self.on_node_click(sid)
                return

    def _on_double_click(self, event):
        mx, my = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        for sn in self._subnodes:
            if sn.get("project_id") is None:
                continue
            h = sn.get("sn_h", self.SUBNODE_H)
            if sn["x"] <= mx <= sn["x"] + self.SUBNODE_W and \
               sn["y"] <= my <= sn["y"] + h:
                if self.on_subnode_double:
                    self.on_subnode_double(sn["project_id"])
                return

    def _on_drag(self, event):
        pass

    def _on_drop(self, event):
        pass

    def _on_zoom(self, event):
        if event.delta > 0:
            self._canvas.scale("all", event.x, event.y, 1.1, 1.1)
        else:
            self._canvas.scale("all", event.x, event.y, 0.9, 0.9)

    def _on_resize(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
