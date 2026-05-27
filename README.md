# 等保测评进度管理系统

基于 Python Tkinter 的桌面端看板应用，用于管理等保测评项目的进度跟踪和流程管理。

**版本**: v2.0.4 | **运行环境**: Windows 7/10/11 | **语言**: Python 3.x

---

## 快速开始

### 方式一：直接运行 EXE（推荐）
下载 [releases/等保测评进度管理系统_v2.0.4.exe](releases/等保测评进度管理系统_v2.0.4.exe)，双击运行，无需安装 Python。

### 方式二：源码运行
```bash
git clone https://github.com/Aj-LLY/dbcp-manager.git
cd dbcp-manager
python main.py
```

---

## 功能概览

| 模块 | 功能描述 |
|------|----------|
| 项目管理 | 新增/编辑/删除项目，字段：公司名称、系统名称、备案号、截止日期、备注 |
| 流程配置 | 默认8阶段等保流程，支持自定义增删改排序及颜色标识 |
| 看板交互 | 卡片展示、箭头按钮移动阶段、详情/编辑按钮、截止日期颜色预警 |
| 数据持久化 | JSON 文件原子写入自动保存，程序重启数据不丢失 |
| 操作日志 | 全量操作记录，支持按项目筛选，时间倒序展示 |
| WebDAV 备份 | 远程备份/恢复/删除，HTTP Basic 认证 |
| 日历选择器 | 可视化弹窗选日期，月份翻页，今天高亮 |

### 默认流程阶段
```
项目启动 → 现状调研 → 差距评估 → 方案设计 → 整改实施 → 测评验收 → 报告输出 → 项目归档
```

---

## 项目结构

```
├── main.py                    # 程序入口
├── build_exe.py               # EXE 打包脚本（自动嵌入版本信息）
├── models/                    # 数据实体层
│   ├── project.py             #   项目实体（公司/系统/备案号/阶段）
│   ├── workflow.py            #   流程阶段实体
│   └── log_entry.py           #   操作日志实体
├── services/                  # 业务服务层
│   ├── data_service.py        #   JSON 持久化（单例模式，原子写入）
│   ├── project_service.py     #   项目 CRUD + 日志回调
│   ├── workflow_service.py    #   流程增删改排序
│   ├── log_service.py         #   日志记录与查询
│   └── backup_service.py      #   WebDAV 备份（PUT/GET/PROPFIND/DELETE）
├── ui/                        # 用户界面层（Tkinter）
│   ├── main_window.py         #   主窗口（MVC 控制器）
│   ├── toolbar.py             #   顶部工具栏
│   ├── kanban_board.py        #   看板主容器
│   ├── kanban_column.py       #   看板列（阶段列）
│   ├── project_card.py        #   项目卡片组件
│   ├── project_dialog.py      #   新增/编辑项目对话框
│   ├── workflow_dialog.py     #   流程配置对话框
│   ├── detail_dialog.py       #   项目详情对话框
│   ├── log_dialog.py          #   操作日志查看器
│   ├── backup_dialog.py       #   WebDAV 备份管理
│   └── calendar_picker.py     #   日历日期选择器
└── utils/                     # 工具模块
    ├── config.py              #   全局配置（版本/颜色/字体/尺寸）
    ├── helpers.py             #   通用函数（ID生成/验证/边框组件）
    ├── logger.py              #   日志文件读写
    └── webdav_config.py       #   WebDAV 连接配置
```

---

## 打包

```bash
python build_exe.py
# 输出: dist/等保测评进度管理系统.exe（约 12MB，带版本信息）
```

右键 EXE → 属性 → 详细信息，可查看文件版本和产品版本。

---

## 版本历史

详见 [CHANGELOG.md](CHANGELOG.md)

## 作者

- GitHub: [Aj-LLY](https://github.com/Aj-LLY)
- 仓库: [dbcp-manager](https://github.com/Aj-LLY/dbcp-manager)
