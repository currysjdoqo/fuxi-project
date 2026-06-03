# 练习题管理系统

一个基于 FastAPI + Vue 3 的在线练习题管理系统，支持题目导入、练习模式、错题本、复习功能和 AI 智能讲解。

## 技术栈

### 后端
- **FastAPI** - 现代高性能的 Web 框架
- **SQLAlchemy** - Python ORM 工具
- **SQLite** - 轻量级数据库
- **Pydantic** - 数据验证

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **Element Plus** - Vue 3 UI 组件库
- **Axios** - HTTP 请求库
- **Vue Router** - Vue 路由管理

## 功能特性

### 1. 题目管理
- 单个添加题目（题目内容、选项、答案、解析）
- 批量导入题目（支持解析带格式的文本）
- 题目分类（科目管理）
- 题目重点标记
- 题目删除与恢复

### 2. 练习模式
- 左侧题目列表（显示题号、题干摘要、对错状态）
- 右侧答题区域（单选、提交、即时反馈）
- 完成后显示正确率统计
- 答题后显示解析内容

### 3. 错题本
- 自动收集错题记录
- 查看错题的正确答案与用户的错误答案
- 重做功能（跳转练习模式并选中该题）
- 移除已掌握题目

### 4. 复习模式
- 从错题本中随机抽取题目
- 可设置抽取数量
- 答对自动移出错题本
- 答错留在错题本并更新复习次数
- 完成后显示正确率统计

### 5. AI 智能讲解（可选）
- 调用 DeepSeek API 生成详细解题思路
- 知识点扩展说明
- 需要在设置中配置 API Key

### 6. 学习计划浮窗
- 可拖动浮窗到任意位置，位置自动保存
- 可收缩到侧边栏，点击图标展开
- 点击计划项标记完成并自动移除

### 7. 设置功能
- 配置 DeepSeek API Key
- 清空所有数据

## 项目结构

```
fuxi/
├── main.py                 # 后端入口
├── database.py             # 数据库配置
├── models.py               # 数据模型
├── schemas.py              # Pydantic 模型
├── requirements.txt        # Python 依赖
├── routers/                # API 路由
│   ├── import_router.py    # 导入题目
│   ├── practice.py         # 练习接口
│   ├── wrong.py            # 错题本接口
│   ├── review.py           # 复习接口
│   ├── subjects.py         # 科目管理
│   ├── trash.py            # 垃圾桶
│   └── settings.py         # 设置接口
├── utils/
│   └── parser.py           # 文本解析器
└── frontend/               # 前端项目
    ├── src/
    │   ├── main.js        # 前端入口
    │   ├── App.vue        # 根组件
    │   ├── router/        # 路由配置
    │   ├── api/           # API 调用
    │   └── views/         # 页面组件
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## 安装与运行

### 环境要求
- Python 3.10+
- Node.js 18+

### 后端安装

```bash
# 进入项目目录
cd g:\学校学习\fuxi

# 创建虚拟环境（如果还没有）
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 启动后端服务
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

后端启动成功后，API 文档访问地址：http://localhost:8000/docs

### 前端安装

```bash
# 进入前端目录
cd g:\学校学习\fuxi\frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端启动成功后，访问地址：http://localhost:5173

### 快速启动命令汇总

**终端 1 - 后端**：
```bash
cd g:\学校学习\fuxi
.venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**终端 2 - 前端**：
```bash
cd g:\学校学习\fuxi\frontend
npm run dev
```

## API 接口列表

### 题目相关
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/questions | 获取题目列表 |
| POST | /api/questions | 添加单个题目 |
| DELETE | /api/questions/{id} | 删除题目 |
| PATCH | /api/questions/{id}/important | 设置重点 |
| POST | /api/import | 批量导入题目 |
| POST | /api/import/parse | 解析题目文本 |
| POST | /api/questions/batch-delete | 批量删除 |

### 练习相关
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/practice/submit | 提交答案 |

### 错题本相关
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/wrong-questions | 获取错题列表 |
| DELETE | /api/wrong-questions/{id} | 移出错题 |

### 复习相关
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/review/generate | 生成复习题目集 |
| POST | /api/review/submit | 提交复习答案 |

### 科目相关
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/subjects | 获取科目列表 |
| POST | /api/subjects | 创建科目 |
| DELETE | /api/subjects/{id} | 删除科目 |

### 垃圾桶相关
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/trash | 获取垃圾桶题目 |
| POST | /api/trash/restore | 恢复题目 |
| DELETE | /api/trash/{id} | 永久删除 |

### 设置相关
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/settings | 获取设置 |
| POST | /api/settings/deepseek-key | 保存 DeepSeek Key |
| DELETE | /api/data | 清空所有数据 |

### AI 相关
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/ai/explain | 获取 AI 讲解 |

## 使用说明

### 1. 导入题目

#### 方式一：单个添加
1. 进入"导入"页面
2. 填写题目内容、选项、答案、解析
3. 点击"添加题目"

#### 方式二：批量导入
支持以下格式的文本：
```
一.单选题（共2题,20.0分）

1

机器学习的目标是( )

A、让计算机存储更多数据

B、模拟和实现人类的学习功能

C、提高计算机的运算速度

D、替代人类进行所有工作

正确答案： B 我的答案：B得分： 10.0分

答案解析：

课件中明确指出"机器学习就是让机器(计算机)来模拟和实现人类的学习功能"。
```

### 2. 练习模式

1. 进入首页查看题目列表
2. 点击题目开始答题
3. 选择答案后点击"提交"
4. 查看对错反馈和解析
5. 底部查看正确率统计

### 3. 错题本

1. 答题错误自动记录到错题本
2. 进入错题本页面查看
3. 可选择"重做"或"移除"

### 4. 复习模式

1. 进入错题本页面
2. 点击"随机复习"按钮
3. 设置抽取数量（默认10）
4. 开始答题
5. 答对自动移出错题本
6. 完成后查看统计

### 5. AI 讲解

1. 进入设置页面
2. 配置 DeepSeek API Key
3. 在答题页面点击"AI 讲解"按钮

## 常见问题

### Q: 端口被占用怎么办？
```bash
# 查找占用端口的进程
Get-NetTCPConnection -LocalPort 8000

# 关闭进程
Stop-Process -Id <PID> -Force
```

### Q: 如何更新代码？
后端使用了 `--reload` 参数，代码修改后会自动重载。前端需要手动刷新浏览器。

### Q: 数据存储在哪里？
使用 SQLite 数据库，文件为 `test.db`，与项目文件在同一目录下。

## License

MIT License