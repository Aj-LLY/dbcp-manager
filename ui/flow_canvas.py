"""
流程图画布模块 -- 等保测评进度管理系统

自由连线模式：右键节点→连线到→选目标→建立连接
"""
from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.project import Project
    from models.workflow import WorkflowStage


class FlowCanvas(tk.Frame):
    """流程图画布：阶段节点 + 项目子节点 + 自由连线 + 拖拽。"""

    NODE_W = 180
    NODE_H = 56
    SUBNODE_W = 190
    SUBNODE_H = 32
    H_GAP = 40
    V_GAP = 30
    SUBNODE_V_GAP = 4

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#f5f6fa", **kwargs)
        self._canvas = tk.Canvas(self, bg="#f5f6fa", highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._stages = []
        self._merged = []
        self._nodes = {}
        self._subnodes = []
        self._connections = []   # [(from_id, to_id), ...]
        self._line_data = {}     # {(from,to): canvas_line_id}
        self.on_node_click = None
        self.on_subnode_click = None
        self.on_subnode_double = None
        self._drag_tag = None
        self._drag_dx = 0
        self._drag_dy = 0
        self._hover_tip = None
        self._connecting_from = None
        self._context_menu = None
        self._sn_drag = None     # 子节点拖拽: {pid, sid, x, y}
        self._bind_events()

    def _bind_events(self):
        self._canvas.bind("<Double-Button-1>", self._on_double_click)
        self._canvas.bind("<Button-3>", self._on_right_click)
        self._canvas.bind("<MouseWheel>", self._on_zoom)
        # 画布平移：左键拖拽空白区 / 中键 / Ctrl+左键
        self._canvas.bind("<Button-1>", self._on_canvas_click, add="+")
        self._canvas.bind("<B1-Motion>", self._on_canvas_drag, add="+")
        self._canvas.bind("<ButtonRelease-1>", self._on_canvas_release, add="+")
        self._canvas.bind("<Button-2>", self._start_pan)
        self._canvas.bind("<B2-Motion>", self._do_pan)
        self._pan_x = 0
        self._pan_y = 0
        self._blank_drag = False
        self._blank_start = (0, 0)
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

        # 初始化默认连线（按 stage order）
        if not self._connections:
            for i in range(len(self._stages) - 1):
                self._connections.append((self._stages[i].id, self._stages[i+1].id))

        print(f'[Flow] load: stages={len(stages)} projects={len(projects)} merged={len(self._merged)}')
        print(f'[Flow] connections={self._connections}')
        self.update_idletasks()
        try:
            try:
                self._auto_layout()
            except Exception as e:
                import traceback
                print(f'[Flow] ⛔ _auto_layout 异常: {e}')
                traceback.print_exc()
        except Exception:
            import traceback
            traceback.print_exc()

    def _auto_layout(self):
        self._canvas.delete("all")
        self._nodes.clear()
        self._subnodes.clear()
        self._line_data.clear()
        if not self._stages:
            return

        # 竖版布局：节点纵向排列
        x = 40
        y = 40
        for i, stage in enumerate(self._stages):

            color = stage.color or "#3498db"
            tag = f"node_{stage.id}"
            elements = []

            rid = self._draw_rounded_rect(x, y, self.NODE_W, self.NODE_H,
                                          fill=color, outline=color, tags=tag)
            elements.append(rid)
            tid = self._canvas.create_text(
                x + self.NODE_W // 2, y + self.NODE_H // 2 - 6,
                text=stage.name, fill="white",
                font=("Microsoft YaHei", 10, "bold"), anchor="center", tags=tag)
            elements.append(tid)
            cnt = sum(1 for g in self._merged if g[0].stage_id == stage.id)
            cid = self._canvas.create_text(
                x + self.NODE_W // 2, y + self.NODE_H // 2 + 12,
                text=str(cnt), fill="#cccccc",
                font=("Microsoft YaHei", 9), anchor="center", tags=tag)
            elements.append(cid)

            for _el in elements:
                self._canvas.tag_bind(_el, "<Button-1>",
                    lambda e, t=tag: self._start_drag(t, e))
                self._canvas.tag_bind(_el, "<B1-Motion>",
                    lambda e, t=tag: self._do_drag(t, e))
                self._canvas.tag_bind(_el, "<ButtonRelease-1>",
                    lambda e: self._end_drag())
                self._canvas.tag_bind(_el, "<Button-3>",
                    lambda e, sid=stage.id: self._show_node_menu(e, sid))

            self._nodes[stage.id] = {"x": x, "y": y, "tag": tag, "elements": elements}
            m_groups = [g for g in self._merged if g[0].stage_id == stage.id]

            # 子节点在当前阶段下方
            sub_y = y + self.NODE_H + 10

            # 更新下一阶段的Y坐标
            sub_total = len(m_groups) * (self.SUBNODE_H + self.SUBNODE_V_GAP) + 30
            y += self.NODE_H + max(sub_total, 20) + 30
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

                rid = self._draw_rounded_rect(sx, sy, self.SUBNODE_W, sn_h,
                                              fill="white", outline="#d0d5dd",
                                              tags=(subtag,))
                bar_color = self._get_status_color(first)
                for p in group:
                    c = self._get_status_color(p)
                    if c == "#ff0000":
                        bar_color = c
                        break
                    if c == "#ffc000" and bar_color != "#ff0000":
                        bar_color = c
                self._canvas.create_rectangle(
                    sx, sy, sx + 6, sy + sn_h, fill=bar_color, outline="", tags=(subtag,))
                self._canvas.create_text(
                    sx + 36, sy + 12, text=title, fill="#2c3e50",
                    font=("Microsoft YaHei", 8, "bold"), anchor="w", tags=(subtag,))
                if is_multi:
                    st = " | ".join((p.system_name or "")[:6] for p in group[:5])
                    if len(st) > 24:
                        st = st[:23] + "…"
                    self._canvas.create_text(
                        sx + 36, sy + 24, text=st, fill="#7f8c8d",
                        font=("Microsoft YaHei", 7), anchor="w", tags=(subtag,))

                for item in self._canvas.find_withtag(subtag):
                    self._canvas.tag_bind(item, "<Button-1>",
                        lambda e, pid=first.id: self._on_sn_click(pid))
                    self._canvas.tag_bind(item, "<Double-Button-1>",
                        lambda e, pid=first.id: self._on_sn_double(pid))
                    self._canvas.tag_bind(item, "<Enter>",
                        lambda e, g=group: self._show_tooltip(e, g))
                    self._canvas.tag_bind(item, "<Leave>", lambda e: self._hide_tooltip())
                    # Shift+拖拽：移动项目到其他阶段
                    self._canvas.tag_bind(item, "<Shift-B1-Motion>",
                        lambda e, pid=first.id, sid=stage.id: self._sn_drag_move(e, pid, sid))
                    self._canvas.tag_bind(item, "<ButtonRelease-1>",
                        lambda e, pid=first.id, sid=stage.id: self._sn_drag_drop(e, pid, sid),
                        add="+")

                self._subnodes.append({
                    "tag": subtag, "x": sx, "y": sy, "sn_h": sn_h,
                    "project_id": first.id, "all_ids": [p.id for p in group],
                    "group": group, "stage_id": stage.id})

            if len(m_groups) > 8:
                self._canvas.create_text(
                    x + self.NODE_W // 2,
                    sub_y + 8 * (self.SUBNODE_H + self.SUBNODE_V_GAP),
                    text=f"+{len(m_groups) - 8} 更多", fill="#95a5a6",
                    font=("Microsoft YaHei", 8), anchor="center")

        self._draw_all_lines()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    # =========================================================================
    # 自由连线
    # =========================================================================

    def _draw_all_lines(self):
        """根据 _connections 绘制所有连线。"""
        self._line_data.clear()
        # 删除旧线（用 find_withtag 找 line_ 开头的）
        for item in self._canvas.find_all():
            tags = self._canvas.gettags(item)
            if any(t.startswith("line_") for t in tags):
                continue  # Already part of node drag system, skip
        # Draw new
        for fid, tid in self._connections:
            if fid in self._nodes and tid in self._nodes:
                self._draw_one_line(fid, tid)

    def _draw_one_line(self, from_id, to_id):
        """竖版连线：从上方节点右侧引出，向下弯曲到下方节点左侧。"""
        n1, n2 = self._nodes[from_id], self._nodes[to_id]
        x1 = n1["x"] + self.NODE_W
        y1 = n1["y"] + self.NODE_H // 2
        x2 = n2["x"]
        y2 = n2["y"] + self.NODE_H // 2
        # 竖版连接线：先向右再向下
        mx = x1 + 40  # 向右偏移
        tag = f"line_{from_id}_{to_id}"
        lid = self._canvas.create_line(
            x1, y1, mx, y1, mx, y2, x2, y2,
            smooth=True, fill="#b0b8c1", width=2,
            arrow=tk.LAST, arrowshape=(8, 10, 3), tags=(tag,))
        self._line_data[(from_id, to_id)] = lid

    def _show_node_menu(self, event, stage_id):
        """右键节点：弹出连线操作菜单。"""
        if self._context_menu:
            self._context_menu.destroy()

        if self._connecting_from is not None:
            # 正在连线模式：点击目标完成连线
            if stage_id != self._connecting_from:
                key = (self._connecting_from, stage_id)
                if key not in self._connections:
                    self._connections.append(key)
                # 删除旧线重绘
                old_key = (self._connecting_from, stage_id)
                if old_key in self._line_data:
                    self._canvas.delete(self._line_data[old_key])
                self._draw_one_line(self._connecting_from, stage_id)
            self._connecting_from = None
            return

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="🔗 连线到...",
            command=lambda: self._start_connect(stage_id))
        menu.add_command(label="❌ 删除全部连线",
            command=lambda: self._clear_node_lines(stage_id))
        menu.add_separator()
        menu.add_command(label="✖ 取消", command=lambda: None)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _start_connect(self, stage_id):
        """开始连线模式。"""
        self._connecting_from = stage_id

    def _clear_node_lines(self, stage_id):
        """删除与该节点相关的所有连线。"""
        removed = []
        for key in list(self._connections):
            if stage_id in key:
                removed.append(key)
        for key in removed:
            self._connections.remove(key)
            if key in self._line_data:
                self._canvas.delete(self._line_data.pop(key))

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
    # 拖拽
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
        dragged_sid = ""
        for sid, nd in self._nodes.items():
            if nd["tag"] == tag:
                nd["x"] += dx
                nd["y"] += dy
                dragged_sid = sid
                break
        if dragged_sid:
            for sn in self._subnodes:
                if sn.get("stage_id") == dragged_sid:
                    for el in self._canvas.find_withtag(sn["tag"]):
                        self._canvas.move(el, dx, dy)
                    sn["x"] += dx
                    sn["y"] += dy
            self._update_lines_for_node(dragged_sid)
        self._drag_dx = event.x
        self._drag_dy = event.y

    def _update_lines_for_node(self, sid):
        """竖版连线更新：出线=从节点右侧到mx再向下，入线=从上方到节点左侧。"""
        nd = self._nodes[sid]
        x, y = nd["x"], nd["y"]
        for key, lid in list(self._line_data.items()):
            if sid not in key:
                continue
            coords = self._canvas.coords(lid)
            if key[0] == sid:  # 出线 (x1,y1, mx,y1, mx,y2, x2,y2)
                coords[0] = x + self.NODE_W
                coords[1] = y + self.NODE_H // 2
                coords[2] = coords[0] + 40
                coords[3] = y + self.NODE_H // 2
            else:  # 入线
                coords[4] = coords[0] + 40  # mx stays same
                coords[5] = y + self.NODE_H // 2
                coords[6] = x
                coords[7] = y + self.NODE_H // 2
            self._canvas.coords(lid, *coords)

    def _end_drag(self):
        self._drag_tag = None

    def _start_pan(self, event):
        self._pan_x = event.x
        self._pan_y = event.y
        self._canvas.configure(cursor="fleur")

    def _do_pan(self, event):
        dx = event.x - self._pan_x
        dy = event.y - self._pan_y
        self._canvas.scan_dragto(-dx, -dy, gain=1)
        self._pan_x = event.x
        self._pan_y = event.y

    # =========================================================================
    # 点击事件
    # =========================================================================

    def _on_sn_click(self, pid):
        print(f'[Flow] _on_sn_click: pid={pid}')
        if self.on_subnode_click:
            print(f'[Flow]   calling on_subnode_click callback')
            self.on_subnode_click(pid)
        else:
            print(f'[Flow]   ⚠ on_subnode_click is None!')

    def _on_sn_double(self, pid):
        print(f'[Flow] _on_sn_double: pid={pid}')
        if self.on_subnode_double:
            self.on_subnode_double(pid)
        else:
            print(f'[Flow]   ⚠ on_subnode_double is None!')

    def _sn_drag_move(self, event, pid, sid):
        """Shift+拖拽子节点：高亮目标阶段。"""
        if self._sn_drag is None:
            self._sn_drag = {"pid": pid, "sid": sid}
        mx, my = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        for stage_id, nd in self._nodes.items():
            if nd["x"] <= mx <= nd["x"] + self.NODE_W and \
               nd["y"] <= my <= nd["y"] + self.NODE_H:
                for el in self._canvas.find_withtag(nd["tag"]):
                    self._canvas.itemconfigure(el, outline="#FFD700", width=3)
            else:
                for el in self._canvas.find_withtag(nd["tag"]):
                    self._canvas.itemconfigure(el, outline=nd["stage"].color or "#3498db", width=1)

    def _sn_drag_drop(self, event, pid, sid):
        """释放子节点：如果落在其他阶段上，触发移动回调。"""
        if self._sn_drag is None:
            self._sn_drag = None
            return
        mx, my = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        target_sid = None
        for stage_id, nd in self._nodes.items():
            if nd["x"] <= mx <= nd["x"] + self.NODE_W and \
               nd["y"] <= my <= nd["y"] + self.NODE_H:
                target_sid = stage_id
                break
        # 恢复边框
        for stage_id, nd in self._nodes.items():
            for el in self._canvas.find_withtag(nd["tag"]):
                self._canvas.itemconfigure(el, outline=nd["stage"].color or "#3498db", width=1)
        if target_sid and target_sid != sid and self.on_subnode_move:
            self.on_subnode_move(pid, target_sid)
        self._sn_drag = None

    def _on_canvas_click(self, event):
        """左键点击：判断是空白区还是节点区。空白区开始平移。"""
        mx, my = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        # 检查是否在某个节点区域内
        for sid, nd in self._nodes.items():
            if nd["x"] <= mx <= nd["x"] + self.NODE_W and \
               nd["y"] <= my <= nd["y"] + self.NODE_H:
                return  # 节点区域，不处理(由tag bind处理)
        for sn in self._subnodes:
            h = sn.get("sn_h", self.SUBNODE_H)
            if sn.get("project_id") and \
               sn["x"] <= mx <= sn["x"] + self.SUBNODE_W and \
               sn["y"] <= my <= sn["y"] + h:
                return  # 子节点区域，不处理
        # 空白区域：开始平移
        self._blank_drag = True
        self._blank_start = (event.x, event.y)
        self._canvas.configure(cursor="fleur")

    def _on_canvas_drag(self, event):
        """空白区拖拽平移。"""
        if self._blank_drag:
            dx = event.x - self._blank_start[0]
            dy = event.y - self._blank_start[1]
            self._canvas.scan_dragto(-dx, -dy, gain=1)
            self._blank_start = (event.x, event.y)

    def _on_canvas_release(self, event):
        self._blank_drag = False
        self._canvas.configure(cursor="")

    def _on_right_click(self, event):
        self._connecting_from = None

    def _on_double_click(self, event):
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
            lines.append(f"等级: {first.level or '-'}")
        self._hover_tip = self._canvas.create_text(
            event.x + 160, event.y + 20,
            text="\n".join(lines), fill="#2c3e50",
            font=("Microsoft YaHei", 8), anchor="w")

    def _hide_tooltip(self):
        if self._hover_tip:
            self._canvas.delete(self._hover_tip)
            self._hover_tip = None

    def _on_zoom(self, event):
        if event.delta > 0:
            self._canvas.scale("all", event.x, event.y, 1.1, 1.1)
        else:
            self._canvas.scale("all", event.x, event.y, 0.9, 0.9)

    def _on_resize(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
