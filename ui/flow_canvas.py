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
        self._nodes = {}      # {stage_id: {"x","y","tag","elements":[ids]}}
        self._subnodes = []   # [{tag, project_id, all_ids, x, y, sn_h}]
        self.on_node_click = None
        self.on_subnode_click = None
        self.on_subnode_double = None
        self.on_subnode_move = None
        self._drag_tag = None
        self._drag_dx = 0
        self._drag_dy = 0
        self._hover_tip = None
        self._bind_events()

    def _bind_events(self):
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Double-Button-1>", self._on_double_click)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_drop)
        self._canvas.bind("<MouseWheel>", self._on_zoom)
        self._canvas.bind("<Motion>", self._on_motion)
        self.bind("<Configure>", self._on_resize)

    def bind_callbacks(self, on_node_click=None, on_subnode_click=None,
                       on_subnode_double=None, on_subnode_move=None):
        self.on_node_click = on_node_click
        self.on_subnode_click = on_subnode_click
        self.on_subnode_double = on_subnode_double
        self.on_subnode_move = on_subnode_move

    # =========================================================================
    # 数据加载
    # =========================================================================

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
        except Exception:
            import traceback
            traceback.print_exc()

    def _auto_layout(self):
        self._canvas.delete("all")
        self._nodes.clear()
        self._subnodes.clear()
        if not self._stages:
            return

        COLS = 4
        for i, stage in enumerate(self._stages):
            col = i % COLS
            row = i // COLS
            x = 60 + col * (self.NODE_W + self.H_GAP)
            y = 40 + row * (self.NODE_H + self.V_GAP + 80)

            color = stage.color or "#3498db"
            tag = f"node_{stage.id}"
            elements = []

            # 阶段节点背景
            rid = self._draw_rounded_rect(x, y, self.NODE_W, self.NODE_H,
                                          fill=color, outline=color, tags=tag)
            elements.append(rid)
            # 阶段名称
            tid = self._canvas.create_text(
                x + self.NODE_W // 2, y + self.NODE_H // 2 - 6,
                text=stage.name, fill="white",
                font=("Microsoft YaHei", 10, "bold"), anchor="center", tags=tag)
            elements.append(tid)
            # 项目计数
            cnt = sum(1 for g in self._merged if g[0].stage_id == stage.id)
            cid = self._canvas.create_text(
                x + self.NODE_W // 2, y + self.NODE_H // 2 + 12,
                text=str(cnt), fill="#cccccc",
                font=("Microsoft YaHei", 9), anchor="center", tags=tag)
            elements.append(cid)

            # 绑定拖拽事件到该 tag 的所有元素
            for _el in elements:
                self._canvas.tag_bind(_el, "<Button-1>",
                    lambda e, t=tag: self._start_drag(t, e))
                self._canvas.tag_bind(_el, "<B1-Motion>",
                    lambda e, t=tag: self._do_drag(t, e))
                self._canvas.tag_bind(_el, "<ButtonRelease-1>",
                    lambda e: self._end_drag())

            self._nodes[stage.id] = {
                "x": x, "y": y, "tag": tag, "elements": elements}

            # 子节点
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

                subtag = f"sn_{first.id}"
                subtag2 = f"sn2_{first.id}"
                items = []

                rid = self._draw_rounded_rect(sx, sy, self.SUBNODE_W, sn_h,
                                              fill="white", outline="#d0d5dd",
                                              tags=(subtag, subtag2))
                items.append(rid)

                bar_color = self._get_status_color(first)
                for p in group:
                    c = self._get_status_color(p)
                    if c == "#ff0000":
                        bar_color = c
                        break
                    if c == "#ffc000" and bar_color != "#ff0000":
                        bar_color = c
                self._canvas.create_rectangle(
                    sx, sy, sx + 6, sy + sn_h, fill=bar_color, outline="",
                    tags=(subtag, subtag2))

                self._canvas.create_text(
                    sx + 36, sy + 12, text=title, fill="#2c3e50",
                    font=("Microsoft YaHei", 8, "bold"), anchor="w",
                    tags=(subtag, subtag2))

                if is_multi:
                    st = " | ".join((p.system_name or "")[:6] for p in group[:5])
                    if len(st) > 24:
                        st = st[:23] + "…"
                    self._canvas.create_text(
                        sx + 36, sy + 24, text=st, fill="#7f8c8d",
                        font=("Microsoft YaHei", 7), anchor="w",
                        tags=(subtag, subtag2))

                # 事件绑定
                for item in self._canvas.find_withtag(subtag):
                    self._canvas.tag_bind(item, "<Button-1>",
                        lambda e, pid=first.id: self._on_sn_click(pid))
                    self._canvas.tag_bind(item, "<Double-Button-1>",
                        lambda e, pid=first.id: self._on_sn_double(pid))
                    self._canvas.tag_bind(item, "<Enter>",
                        lambda e, g=group: self._show_tooltip(e, g))
                    self._canvas.tag_bind(item, "<Leave>",
                        lambda e: self._hide_tooltip())

                self._subnodes.append({
                    "tag": subtag, "x": sx, "y": sy, "sn_h": sn_h,
                    "project_id": first.id, "all_ids": [p.id for p in group],
                    "group": group})

            if len(m_groups) > 8:
                self._canvas.create_text(
                    x + self.NODE_W // 2,
                    sub_y + 8 * (self.SUBNODE_H + self.SUBNODE_V_GAP),
                    text=f"+{len(m_groups) - 8} 更多", fill="#95a5a6",
                    font=("Microsoft YaHei", 8), anchor="center")

        # 阶段间连线
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

    # =========================================================================
    # 绘图工具
    # =========================================================================

    def _draw_rounded_rect(self, x, y, w, h, fill, outline, radius=10, tags=None):
        coords = (x + radius, y, x + w - radius, y, x + w, y, x + w, y + radius,
                  x + w, y + h - radius, x + w, y + h, x + w - radius, y + h,
                  x + radius, y + h, x, y + h, x, y + h - radius,
                  x, y + radius, x, y)
        return self._canvas.create_polygon(coords, fill=fill, outline=outline,
                                           smooth=True, width=1, tags=tags)

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

    # =========================================================================
    # 拖拽（节点级，通过 tag 绑定）
    # =========================================================================

    def _start_drag(self, tag, event):
        self._drag_tag = tag
        self._drag_dx = event.x
        self._drag_dy = event.y

    def _do_drag(self, tag, event):
        if self._drag_tag != tag:
            return
        dx = event.x - self._drag_dx
        dy = event.y - self._drag_dy
        for el in self._canvas.find_withtag(tag):
            self._canvas.move(el, dx, dy)
        # 更新存储的位置
        for sid, nd in self._nodes.items():
            if nd["tag"] == tag:
                nd["x"] += dx
                nd["y"] += dy
                break
        self._drag_dx = event.x
        self._drag_dy = event.y

    def _end_drag(self):
        self._drag_tag = None

    # =========================================================================
    # 点击事件
    # =========================================================================

    def _on_sn_click(self, pid):
        if self.on_subnode_click:
            self.on_subnode_click(pid)

    def _on_sn_double(self, pid):
        if self.on_subnode_double:
            self.on_subnode_double(pid)

    def _on_click(self, event):
        # 由 tag 绑定处理，此处留空
        pass

    def _on_double_click(self, event):
        pass

    def _on_drag(self, event):
        pass

    def _on_drop(self, event):
        pass

    # =========================================================================
    # 悬停 tooltip
    # =========================================================================

    def _show_tooltip(self, event, group):
        if self._hover_tip:
            self._canvas.delete(self._hover_tip)
        first = group[0]
        lines = []
        if len(group) > 1:
            lines.append(f"公司: {first.company_name}")
            for p in group:
                lines.append(f"  系统: {p.system_name or '-'}  等级: {p.level or '-'}")
        else:
            lines.append(f"系统: {first.system_name or '-'}")
            lines.append(f"公司: {first.company_name or '-'}")
            lines.append(f"等级: {first.level or '-'}  证书: {first.cert_number or '-'}")
        self._hover_tip = self._canvas.create_text(
            event.x + 160, event.y + 20,
            text="\n".join(lines), fill="#2c3e50",
            font=("Microsoft YaHei", 8), anchor="w",
        )

    def _hide_tooltip(self):
        if self._hover_tip:
            self._canvas.delete(self._hover_tip)
            self._hover_tip = None

    def _on_motion(self, event):
        pass

    def _on_zoom(self, event):
        if event.delta > 0:
            self._canvas.scale("all", event.x, event.y, 1.1, 1.1)
        else:
            self._canvas.scale("all", event.x, event.y, 0.9, 0.9)

    def _on_resize(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
