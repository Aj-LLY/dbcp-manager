# 项目进度管理系统

基于 Python Tkinter 的桌面端看板应用，用于管理项目的进度跟踪和流程管理。采用 MVC 三层架构，支持自定义流程阶段、可视化看板交互、备案证 OCR 识别、WebDAV 远程备份及完整的操作日志追溯。

**版本**: v3.0.0 | **运行环境**: Windows 7/10/11 | **语言**: Python 3.x

---

## 功能概览

| 模块 | 功能描述 |
|------|----------|
| 看板管理 | 卡片式展示、箭头按钮移动阶段、拖拽调整列宽、鼠标滚轮翻页、截止日期颜色预警 |
| 项目管理 | 新增/编辑/删除/复制项目，支持公司名称、系统名称、系统等级、证书编号、属地、下证日期、交付日期、备注 |
| 备案证 OCR | 上传备案证 PDF/图片自动识别：公司名称、系统名称、证书编号、系统等级、下证日期（需 `pip install easyocr PyMuPDF`） |
| 流程配置 | 默认 8 阶段等保测评流程，支持自定义增删改查排序、颜色标识、独立列宽设置 |
| 项目详情 | 双击卡片弹出详情窗口，查看完整信息、操作历史、阶段移动、编辑/删除 |
| 数据持久化 | JSON 文件原子写入（tempfile + os.replace），程序重启数据不丢失 |
| 操作日志 | 全量操作记录，支持按项目筛选，阶段变更格式：`项目名：旧阶段 → 新阶段` |
| WebDAV 备份 | 远程备份/恢复/删除，HTTP Basic 认证，恢复后自动刷新数据无需重启 |
| 项目文件夹 | 新建项目自动创建 `{序号}-{公司}-{系统}-{日期}` 目录结构，支持一键重命名和打包 |
| 报告打印 | 弹出编辑确认框 → 生成测评报告打印信息 XLSX → 复制附件到报告打印目录 |
| 属地区域 | 省市区两级联动下拉选择，覆盖 34 个省级行政区 |
| 日历选择器 | 可视化弹窗选日期，月份/年份翻页，今天高亮，快捷日期按钮 |

### 默认流程阶段

```
项目启动 → 现状调研 → 差距评估 → 方案设计 → 整改实施 → 测评验收 → 报告输出 → 项目归档
```

---

## 快速开始

### 方式一：直接运行 EXE

下载 [Releases](https://github.com/Aj-LLY/dbcp-manager/releases) 中最新的 `项目进度管理系统_vX.X.X.exe`，双击运行。

### 方式二：源码运行

```bash
git clone https://github.com/Aj-LLY/dbcp-manager.git
cd dbcp-manager
python main.py
```

### OCR 识别功能（可选）

```bash
pip install easyocr PyMuPDF
```

---

## 项目架构

```
项目进度管理系统/
├── main.py                    # 程序入口
├── build_exe.py               # EXE 打包脚本
├── release.py                 # GitHub Release 发布脚本
├── models/                    # 数据实体层
│   ├── project.py             #   项目实体（14 个字段 + 序列化 + 旧数据兼容）
│   ├── workflow.py            #   流程阶段实体（名称/排序/颜色/列宽）
│   └── log_entry.py           #   操作日志实体（7 种操作类型常量）
├── services/                  # 业务服务层
│   ├── data_service.py        #   JSON 持久化（单例/原子写入/reload）
│   ├── project_service.py     #   项目 CRUD（创建/更新/删除/阶段移动/日志回调）
│   ├── workflow_service.py    #   流程管理（增删改查/排序/重置/列宽）
│   ├── log_service.py         #   日志追踪（记录/查询/回调工厂）
│   ├── backup_service.py      #   WebDAV 备份（PUT/GET/PROPFIND/DELETE + 时区转换）
│   └── cert_ocr.py            #   备案证 OCR（easyocr + PyMuPDF + 字段提取）
├── ui/                        # 用户界面层（Tkinter）
│   ├── main_window.py         #   主窗口控制器（MVC 协调/事件分发/项目文件夹创建）
│   ├── toolbar.py             #   顶部工具栏
│   ├── kanban_board.py        #   看板容器（双向滚动/列管理/卡片选中/阶段移动）
│   ├── kanban_column.py       #   看板列（标题+计数/卡片滚动/拖拽列宽）
│   ├── project_card.py        #   项目卡片（状态色条/箭头/14 个操作按钮/tooltip/报告打印）
│   ├── project_dialog.py      #   项目编辑对话框（14 字段/省市级联/OCR/日历/文件夹管理）
│   ├── workflow_dialog.py     #   流程配置对话框（Treeview 表格/增删改排序/列宽编辑）
│   ├── detail_dialog.py       #   项目详情对话框（信息展示/阶段移动/编辑删除/日志摘要）
│   ├── log_dialog.py          #   操作日志查看器（表格展示/项目筛选/双滚动条）
│   ├── backup_dialog.py       #   WebDAV 备份对话框（双标签页/配置/备份恢复删除）
│   └── calendar_picker.py     #   日历选择器（月/年翻页/今天高亮/快捷按钮）
└── utils/                     # 工具模块
    ├── config.py              #   全局配置（版本/流程/颜色/字体/尺寸/路径策略）
    ├── helpers.py             #   通用函数（ID 生成/日期计算/名称校验/证书编号/边框输入框）
    ├── logger.py              #   日志记录器（内存+文件双写）
    └── webdav_config.py       #   WebDAV 配置管理
```

---

## 卡片按钮说明

```
┌──────────────────────────┐
│  系统名称 (粗体)          │
│  公司名称                 │
│  第二级  📜 已备案 xxx    │
│  📅 交付日期              │
│                          │
│  [详情] [编辑] [复制]     │  ← 第1行：项目操作
│  [📂] [📝] [📦] [📄]     │  ← 第2行：文件操作 (悬浮提示)
└──────────────────────────┘
```

| 按钮 | 功能 |
|------|------|
| 详情 | 打开项目详情窗口 |
| 编辑 | 打开项目编辑对话框 |
| 复制 | 创建项目副本（追加"-副本"后缀） |
| 📂 | 打开项目文件夹 |
| 📝 | 批量重命名文件（含 ZIP 解压） |
| 📦 | 打包过程文档为 ZIP |
| 📄 | 报告打印（编辑确认 → XLSX → 复制附件） |

---

## 打包

```bash
python build_exe.py
# 输出: dist/项目进度管理系统_v3.0.0.exe（约 266MB，含 OCR 引擎）
```

---

## 版本历史

详见 [CHANGELOG.md](CHANGELOG.md)

## 作者

- GitHub: [Aj-LLY](https://github.com/Aj-LLY)
- 仓库: [dbcp-manager](https://github.com/Aj-LLY/dbcp-manager)
