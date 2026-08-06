# 等保测评项目进度管理系统

基于 Python Tkinter 的桌面端看板应用，用于管理等保测评项目的进度跟踪和流程管理。遵循 8 条编码与架构原则（分层/依赖倒置/配置分离/接口稳定/技术隔离/自动化测试/显式优于隐式/Karpathy准则）。

**版本**: v4.5.0 | **运行环境**: Windows 10/11 | **语言**: Python 3.12+

---

## 功能概览

| 模块 | 功能描述 |
|------|----------|
| 看板管理 | 5 色状态条（绿/蓝/黄/红/灰）、箭头移动阶段、拖拽列宽、滚轮翻页、截止日期预警 |
| 项目管理 | 新增/编辑/删除/复制项目，14 个字段，支持多系统合并卡片 |
| 备案证 OCR | 上传备案证 PDF/图片自动识别字段（需 `pip install easyocr PyMuPDF`） |
| 流程配置 | 默认 8 阶段等保测评流程，支持自定义增删改查排序、颜色标识 |
| 项目详情 | 双击卡片查看完整信息、操作历史、阶段移动、结项判定 |
| 数据持久化 | JSON 文件原子写入，重启数据不丢失 |
| 操作日志 | 全量记录，按项目筛选，阶段变更格式化 |
| WebDAV 备份 | 远程备份/恢复/删除，HTTP Basic 认证 |
| 项目文件夹 | 自动创建标准目录结构，一键重命名、打包、初始化 |
| 报告打印 | 编辑确认 → 复制附件 → 生成 XLSX（OLE 链接对象）→ Office/WPS 双击打开 |
| 属地区域 | 省市区两级联动下拉 |
| 日历选择器 | 可视化选日期，月份翻页，今天高亮 |

### 卡片状态色

| 颜色 | 含义 | 触发条件 |
|------|------|----------|
| 🟢 `#92d050` | 已完成 | 处于最后流程阶段（结项） |
| 🔵 `#00b0f0` | 进行中 | 截止日期充裕（> 7天） |
| 🟡 `#ffc000` | 需关注 | 截止日期临近（≤ 7天） |
| 🔴 `#ff0000` | 严重延误 | 已超期 |
| ⚪ `#d9d9d9` | 无日期 | 未设置截止日期 |

---

## 快速开始

### 方式一：EXE 运行

下载 [Releases](https://github.com/Aj-LLY/dbcp-manager/releases) 中最新的 `项目进度管理系统_vX.X.X.exe`，双击运行。

### 方式二：源码运行

```bash
git clone https://github.com/Aj-LLY/dbcp-manager.git
cd dbcp-manager
pip install -r requirements.txt
python main.py
```

### OCR 识别（可选）

```bash
pip install easyocr PyMuPDF
```

---

## 项目架构

遵循 8 条编码与架构原则的 MVC 三层结构：

```
等保测评进度管理系统/
├── main.py                    # 程序入口
├── build_exe.py               # EXE 打包脚本
├── release.py                 # GitHub Release 发布脚本
├── models/                    # 数据实体层
│   ├── project.py             #   项目实体
│   ├── workflow.py            #   流程阶段实体
│   ├── log_entry.py           #   操作日志实体
│   └── dto.py                 #   数据传输对象
├── services/                  # 业务服务层（原则 #2 依赖倒置）
│   ├── interfaces.py          #   抽象接口 (IDataService/IProjectService/IWorkflowService/ILogService/IOleEmbedService)
│   ├── data_service.py        #   JSON 持久化
│   ├── project_service.py     #   项目 CRUD
│   ├── workflow_service.py    #   流程管理
│   ├── log_service.py         #   日志追踪
│   ├── backup_service.py      #   WebDAV 备份
│   ├── cert_ocr.py            #   备案证 OCR
│   └── ole_service.py         #   OLE 对象嵌入（Win32Com 实现，原则 #5 技术隔离）
├── controllers/               # 控制器层
│   ├── project_handlers.py    #   项目 CRUD 事件
│   └── startup_handlers.py    #   启动/关闭逻辑
├── ui/                        # 用户界面层（Tkinter）
│   ├── main_window.py         #   主窗口
│   ├── kanban_board.py        #   看板容器
│   ├── kanban_column.py       #   看板列
│   ├── project_card.py        #   项目卡片
│   ├── project_dialog.py      #   项目编辑对话框
│   ├── detail_dialog.py       #   项目详情对话框
│   ├── dialog_report_print.py #   报告打印（XLSX 生成）
│   ├── dialog_project_ocr.py  #   OCR 对话框
│   ├── workflow_dialog.py     #   流程配置
│   ├── backup_dialog.py       #   WebDAV 备份
│   ├── calendar_picker.py     #   日历选择器
│   ├── card_file_ops.py       #   卡片文件操作协调器
│   └── file_ops/              #   文件操作子模块
│       ├── folder_ops.py      #   文件夹操作
│       ├── init_project.py    #   项目初始化
│       ├── rename.py          #   批量重命名
│       └── zip_pack.py        #   过程文档打包
└── utils/                     # 工具模块
    ├── config.py              #   全局配置（原则 #3 配置与代码分离）
    ├── helpers.py             #   通用函数
    └── province_data.py       #   省市区数据
```

---

## 架构原则

| 原则 | 落实 |
|------|------|
| #1 分层与模块化 | models → services → controllers → ui，禁止跨层调用 |
| #2 依赖倒置 | 5 个抽象接口（IDataService/IProjectService/IWorkflowService/ILogService/IOleEmbedService） |
| #3 配置分离 | Config 类管理所有可变配置，无硬编码路径/颜色/ID |
| #4 接口稳定 | 接口仅扩展字段，不删除不修改，保留兼容期 |
| #5 技术隔离 | _FileSerializer 封装加密、Config 封装文件 I/O、ole_service 封装 COM 自动化 |
| #6 自动化测试 | 测试金字塔待建设（单元 → 集成 → E2E） |
| #7 显式优于隐式 | 显式依赖注入、类型注解、异常分类处理、无静默吞异常 |
| #8 Karpathy准则 | 先思考再编码、简单优先、手术式修改、目标驱动执行 |

---

## 打包

```bash
pip install pyinstaller
python build_exe.py
# 输出: dist/项目进度管理系统_v4.5.0.exe（约 266MB，含 OCR 引擎）
```

## 发布

```bash
pip install pyinstaller pywin32
python release.py
# 自动: 构建 EXE → 创建 GitHub Release → 上传资产
```

---

## 版本历史

详见 [CHANGELOG.md](CHANGELOG.md)

## 作者

- GitHub: [Aj-LLY](https://github.com/Aj-LLY)
- 仓库: [dbcp-manager](https://github.com/Aj-LLY/dbcp-manager)
