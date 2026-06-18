# 等保测评项目进度管理系统 — 开发设计方案

> 版本: v4.0.0 | 更新: 2026-06-12 | 作者: Aj-LLY

---

## 1. 项目概述

### 1.1 项目背景

等保测评项目涉及 8 个标准流程阶段、19 类过程文件、多系统并行管理。传统 Excel/纸质管理方式存在信息分散、进度不可视、文件命名不规范、版本混乱等问题。

### 1.2 项目目标

构建一个桌面端看板应用，实现：
- 项目全生命周期可视化跟踪
- 过程文件标准化自动管理
- 报告打印信息一键生成
- 远程备份与数据安全

### 1.3 技术选型

| 层面 | 技术 | 选型理由 |
|------|------|----------|
| 语言 | Python 3.12+ | 生态丰富，快速开发 |
| GUI | Tkinter | 标准库，零依赖部署，Windows 原生支持 |
| Excel | openpyxl + win32com | openpyxl 生成 XLSX，win32com 嵌入 OLE 对象 |
| Word | python-docx | 保密承诺书模板替换 |
| OCR | easyocr + PyMuPDF | 备案证自动识别 |
| 备份 | WebDAV (HTTP) | 自建云存储，无第三方依赖 |
| 打包 | PyInstaller | 单文件 EXE 分发 |

---

## 2. 架构设计

### 2.1 分层架构（原则 #1）

```
┌─────────────────────────────────────────┐
│  UI 层 (ui/)                            │
│  主窗口 / 看板 / 卡片 / 对话框 / 日历    │
├─────────────────────────────────────────┤
│  控制器层 (controllers/)                │
│  事件处理 / 启动逻辑                     │
├─────────────────────────────────────────┤
│  服务层 (services/)                     │
│  接口 (interfaces.py)  ← 原则 #2 DIP   │
│  ┌──────┬──────┬──────┬──────┬───────┐ │
│  │ 项目 │ 流程 │ 日志 │ 备份 │ OCR   │ │
│  │ 服务 │ 服务 │ 服务 │ 服务 │ 服务  │ │
│  └──────┴──────┴──────┴──────┴───────┘ │
├─────────────────────────────────────────┤
│  数据层 (models/)                       │
│  Project / WorkflowStage / LogEntry     │
├─────────────────────────────────────────┤
│  工具层 (utils/)                        │
│  Config / Helpers / ProvinceData        │
└─────────────────────────────────────────┘
```

### 2.2 依赖倒置（原则 #2）

```
services/interfaces.py  ← 抽象接口定义
  ├── IDataService      → DataService
  ├── IProjectService   → ProjectService
  ├── ILogService       → LogService
  └── IOleEmbedService  → Win32ComOleEmbedService  ← 原则 #5 技术隔离
```

### 2.3 技术隔离（原则 #5）

```
业务代码                   技术实现
─────────                  ────────
_report_print()  ──调用──  IOleEmbedService (抽象)
                                │
                     Win32ComOleEmbedService (win32com)
                     可替换为: OpenpyxlOleService (openpyxl)
                               NoopOleService (无 OLE 环境)
```

---

## 3. 模块设计

### 3.1 项目结构（31 个源文件）

```
等保测评进度管理系统/
├── main.py                       # 程序入口
├── build_exe.py                  # PyInstaller 打包
├── release.py                    # GitHub Release 发布
│
├── models/                       # 数据实体层
│   ├── project.py                # Project（14字段 + 序列化）
│   ├── workflow.py               # WorkflowStage
│   ├── log_entry.py              # LogEntry（7种操作类型）
│   └── dto.py                    # 数据传输对象
│
├── services/                     # 业务服务层
│   ├── interfaces.py             # 4个抽象接口
│   ├── project_service.py        # 项目 CRUD + 阶段移动
│   ├── workflow_service.py       # 流程配置管理
│   ├── log_service.py            # 操作日志
│   ├── data_service.py           # JSON 持久化（原子写入）
│   ├── backup_service.py         # WebDAV 远程备份
│   ├── cert_ocr.py               # 备案证 OCR 识别
│   └── ole_service.py            # OLE 对象嵌入
│
├── controllers/                  # 控制器层
│   ├── project_handlers.py       # 项目 CRUD 事件处理
│   └── startup_handlers.py       # 启动/关闭逻辑
│
├── ui/                           # 用户界面层
│   ├── main_window.py            # 主窗口（MVC 协调器）
│   ├── kanban_board.py           # 看板容器（双向滚动）
│   ├── kanban_column.py          # 看板列（卡片管理/拖拽列宽）
│   ├── project_card.py           # 项目卡片（5色状态/14按钮）
│   ├── project_dialog.py         # 项目编辑对话框（14字段/OCR）
│   ├── detail_dialog.py          # 项目详情对话框
│   ├── dialog_report_print.py    # 报告打印（XLSX生成）
│   ├── dialog_project_ocr.py     # OCR 归档
│   ├── workflow_dialog.py        # 流程配置（Treeview表格）
│   ├── backup_dialog.py          # WebDAV 备份对话框
│   ├── calendar_picker.py        # 日历选择器
│   ├── card_file_ops.py          # 卡片文件操作协调器
│   └── file_ops/                 # 文件操作子模块
│       ├── folder_ops.py         # 文件夹查找/打开
│       ├── init_project.py       # 项目初始化
│       ├── rename.py             # 批量重命名
│       └── zip_pack.py           # 过程文档打包
│
└── utils/                        # 工具模块
    ├── config.py                 # 全局配置
    ├── helpers.py                # 通用函数
    ├── tooltip.py                # 悬浮提示
    └── province_data.py          # 省市区数据
```

### 3.2 数据模型

**Project**（14 个字段）：
```
id, company_name, system_name, cert_number, issue_date,
level, location, deadline, notes, stage_id, folder_path,
created_at, updated_at, name
```

**WorkflowStage**（默认 8 阶段）：
```
项目启动 → 现状调研 → 差距评估 → 方案设计 →
整改实施 → 测评验收 → 报告输出 → 项目归档
```

### 3.3 核心功能模块

#### 看板管理
- 卡片式展示：左侧 8px 状态色条 + 公司/系统/日期/按钮
- 5 色状态系统：绿(结项)/蓝(进行中)/黄(需关注)/红(严重延误)/灰(无日期)
- 阶段移动：◀/▶ 箭头按钮，移至最后阶段自动判定结项
- 列宽拖拽：4px 手柄三阶段事件（按下/移动/释放）
- 卡片合并：同公司同阶段项目合并为一张卡片
- 滚轮翻页：列内卡片溢出时启用垂直滚动

#### 项目初始化
创建标准化目录结构：
```
{序号}-{公司}-{系统}-{YYMMDD}/
├── 01-其他归档文件/
│   ├── 00-网安报备
│   ├── 01-备案材料
│   ├── 02-往期测评报告
│   ├── 03-现场测评
│   └── 04-渗透漏扫
└── 02-{公司}-{系统}-保密承诺书.docx
```

#### 批量文件重命名（19 类过程文件）
- ZIP 解压：评审记录表 / 渗透测试报告 / 报告评审表
- 关键词映射：20 个关键词 → 19 个标准编号
- 多系统智能前缀：公司级文件(公司名) / 系统级文件(公司-系统)
- 初审版本清理

#### 报告打印（5 步流程）
```
弹出编辑框(14字段) → 复制附件 → 生成XLSX(openpyxl)
→ OLE链接对象(win32com) → 弹窗汇总
```
XLSX 表格：21 列（序号~实际编制人），O~R 列嵌入文件链接对象。

#### 远程备份（WebDAV）
- HTTP Basic 认证
- 原子写入（tempfile + os.replace）
- GMT→CST 时区转换
- 备份/恢复/删除

#### 备案证 OCR
- easyocr 识别文本 + 正则提取字段
- PyMuPDF 渲染 PDF 为图片
- 归档到 `01-其他归档文件/02-往期测评报告/`

---

## 4. 接口设计

### 4.1 内部接口

| 接口 | 方法 | 职责 |
|------|------|------|
| IDataService | CRUD + save/reload | JSON 数据持久化 |
| IProjectService | create/update/delete/move | 项目生命周期 |
| ILogService | add/get/回调工厂 | 操作日志 |
| IOleEmbedService | embed_files/is_available | OLE 对象嵌入 |

### 4.2 函数签名稳定性（原则 #4）

所有公开函数仅扩展参数（新增可选参数），不删除不修改已有参数。示例：
```python
# v3: 原始签名
def on_init_click(project, parent=None)

# v4: 扩展（新增可选参数，向后兼容）
def on_init_click(project, parent=None, all_projects=None)
```

### 4.3 文件名约定

| 文件 | 命名格式 | 示例 |
|------|----------|------|
| 保密承诺书(单) | `02-{公司}-{系统}-保密承诺书.docx` | `02-XX公司-财务系统-保密承诺书.docx` |
| 保密承诺书(多) | `02-{公司}-保密承诺书.docx` | `02-XX公司-保密承诺书.docx` |
| 过程文档 ZIP(单) | `{公司}-{系统}-过程文档.zip` | `XX公司-财务系统-过程文档.zip` |
| 过程文档 ZIP(多) | `{公司}-过程文档.zip` | `XX公司-过程文档.zip` |
| 报告打印目录 | `00-{公司}-{系统}-报告打印` | `00-XX公司-财务系统-报告打印` |
| XLSX 打印信息 | `00-{公司}-{系统}-测评报告打印信息.xlsx` | `00-XX公司-财务系统-测评报告打印信息.xlsx` |

---

## 5. 配置管理（原则 #3）

```python
class Config:
    APP_VERSION = "4.0.0"
    DEFAULT_WORKFLOW_STAGES = [...]    # 默认 8 阶段
    STATUS_COLORS = {                  # 5 色状态系统
        "completed": "#92d050",  # 绿
        "normal":    "#00b0f0",  # 蓝
        "warning":   "#ffc000",  # 黄
        "overdue":   "#ff0000",  # 红
        "inactive":  "#d9d9d9",  # 灰
    }
    DEADLINE_WARNING_DAYS = 7          # 预警阈值
    FONT_FAMILY = "Microsoft YaHei"
```

所有可变配置集中在 `utils/config.py`，无硬编码路径/颜色/阈值。

---

## 6. 测试策略（原则 #6）

### 测试金字塔

```
        /\
       /E2E\        少量：完整报告打印流程
      /------\
     / 集成测试 \    中等：文件操作 + OLE 嵌入
    /----------\
   /  单元测试   \   大量：服务层 / 工具函数 / 模型
  /--------------\
```

### 重点覆盖

| 层级 | 覆盖目标 |
|------|----------|
| 单元 | `days_until_deadline`、`_get_status_color`、关键词匹配、命名规则 |
| 集成 | `_create_report_xlsx` → `_embed_oles_in_xlsx` 流程 |
| E2E | 新建项目 → 初始化 → 重命名 → 打包 → 报告打印完整链路 |

---

## 7. 异常处理规范（原则 #7）

```python
# ✓ 正确：分层分类处理
try:
    shutil.copy(fpath, dst)
except PermissionError:
    _logger.debug("跳过文件(被锁定): %s", fpath)  # 非关键，记录后继续
except shutil.SameFileError:
    pass  # 源=目标，无需操作

# ✗ 错误：裸 except 吞所有异常
except:
    pass

# ✓ 正确：顶层兜底，显式记录
except Exception as e:
    _logger.exception("报告打印失败")  # 完整 traceback
    messagebox.showerror("错误", f"报告打印失败: {e}")
```

---

## 8. 部署发布

### 开发环境
```bash
git clone https://github.com/Aj-LLY/dbcp-manager.git
cd dbcp-manager
pip install openpyxl python-docx pywin32
# OCR 可选: pip install easyocr PyMuPDF
python main.py
```

### 生产构建
```bash
python build_exe.py
# 输出: dist/项目进度管理系统_v4.0.0.exe (~266MB)
```

### GitHub Release
```bash
python release.py
# 自动: 构建 → 打Tag → 创建Release → 上传资产
```

---

## 9. 版本路线图

| 版本 | 里程碑 |
|------|--------|
| v1.0 | 基础看板 + CRUD |
| v2.0 | WebDAV 备份 + 日历 + 字段拆分 |
| v3.0 | 大型重构 + 文件操作 + 卡片合并 |
| v4.0 | 架构重构 + 7原则落地 + OLE服务抽象 |
| v4.1 | 单元测试覆盖 + CI/CD |
| v5.0 | 数据库迁移 + 多用户 + Web 版 |

---

## 10. 设计原则速查

| # | 原则 | 落实情况 |
|---|------|----------|
| 1 | 分层与模块化 | 4层架构 / 31个模块 / 禁止跨层调用 |
| 2 | 依赖倒置 | 4个抽象接口 / 服务层依赖抽象 |
| 3 | 配置分离 | Config类 / 无硬编码 |
| 4 | 接口稳定 | 仅扩展参数 / 向后兼容 |
| 5 | 技术隔离 | ole_service 封装 win32com |
| 6 | 自动化测试 | 测试金字塔待建设 |
| 7 | 显式优于隐式 | 类型注解 / 异常分类 / logging |
