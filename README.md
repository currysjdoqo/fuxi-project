# 练习题管理系统

一个基于 FastAPI + Vue 3 的在线练习题管理系统，支持题目导入、多种练习模式、错题本、智能复习和 AI 智能讲解。

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
- 题目删除与恢复（垃圾桶功能）

### 2. 练习模式
- **多种练习方式**：
  - 顺序练习：按题目顺序依次练习
  - 范围练习：指定起始题号和结束题号进行练习
  - 随机抽题：随机抽取指定数量的题目
- 左侧题目导航（显示题号、答题状态、对错标记）
- 右侧答题区域（单选、多选、判断、填空、简答、编程题）
- **批量提交**：选择题可加入待提交队列，统一批量提交
- **即时反馈**：答题后立即显示对错和正确答案
- **填空题自判**：用户自行判断是否正确
- **删除题目**：支持删除当前题目
- 完成后显示正确率统计

### 3. 错题本
- 自动收集错题记录
- 查看错题的正确答案与用户的错误答案
- 重做功能（跳转练习模式并选中该题）
- 移除已掌握题目
- 每个科目独立显示错题数量

### 4. 复习模式
- **三种复习方式**：
  - 顺序复习：按顺序复习错题
  - 范围复习：指定题号范围复习
  - 随机抽题：随机抽取错题进行复习
- **每个科目独立设置**：不同科目可使用不同的复习方式
- **批量提交**：选择题支持批量提交
- **填空题自判**：用户自行判断是否正确
- **Enter键提交**：选好答案后按Enter键快速提交
- **错题移除阈值**：答对指定次数（默认3次）后自动移出错题本
- 即时显示正确答案和解析

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
- 错题移除阈值设置

## 项目结构

```
fuxi/
├── main.py                 # 后端入口
├── database.py             # 数据库配置
├── models.py               # 数据模型
├── schemas.py              # Pydantic 模型
├── requirements.txt        # Python 依赖
├── routers/                # API 路由
│   ├── auth.py             # 用户认证
│   ├── import.py           # 导入题目
│   ├── import_router.py    # 导入路由
│   ├── practice.py         # 练习接口
│   ├── wrong.py            # 错题本接口
│   ├── review.py           # 复习接口
│   ├── subjects.py         # 科目管理
│   ├── trash.py            # 垃圾桶
│   ├── plan.py             # 学习计划
│   └── settings.py         # 设置接口
├── utils/
│   ├── parser.py           # 文本解析器
│   ├── file_extract.py     # 文件提取工具
│   └── answer_normalizer.py # 答案标准化工具
└── frontend/               # 前端项目
    ├── src/
    │   ├── main.js         # 前端入口
    │   ├── App.vue         # 根组件
    │   ├── router/         # 路由配置
    │   ├── api/            # API 调用
    │   ├── composables/    # 组合式函数
    │   └── views/          # 页面组件
    │       ├── Home.vue    # 首页/练习模式
    │       ├── Import.vue  # 导入页面
    │       ├── Important.vue # 重点题目
    │       ├── WrongList.vue # 错题本
    │       ├── Review.vue  # 复习模式
    │       ├── Plan.vue    # 学习计划
    │       ├── Settings.vue # 设置
    │       ├── Trash.vue   # 垃圾桶
    │       ├── Login.vue   # 登录
    │       └── Register.vue # 注册
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
cd fuxi

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（Windows）
.venv\Scripts\Activate.ps1

# 激活虚拟环境（Linux/Mac）
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动后端服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端启动成功后，API 文档访问地址：http://localhost:8000/docs

### 前端安装

```bash
# 进入前端目录
cd fuxi/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端启动成功后，访问地址：http://localhost:5173

### 快速启动

**终端 1 - 后端**：
```bash
cd fuxi
.venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**终端 2 - 前端**：
```bash
cd fuxi/frontend
npm run dev
```

## API 接口列表

### 用户认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 用户登录 |
| POST | /api/auth/register | 用户注册 |

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
| POST | /api/review/batch-submit | 批量提交复习答案 |

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

1. 进入首页选择科目
2. 选择练习方式（顺序/范围/随机）
3. 设置练习数量或范围
4. 点击题目开始答题
5. 选择题：选择答案后点击"提交"或按Enter键
6. 填空题：输入答案后自行判断是否正确
7. 查看对错反馈和解析
8. 底部查看正确率统计和待提交数量

### 3. 错题本

1. 答题错误自动记录到错题本
2. 进入错题本页面查看
3. 可选择"重做"或"移除"

### 4. 复习模式

1. 进入复习页面选择科目
2. 选择复习方式（顺序/范围/随机）
3. 设置复习数量或范围
4. 点击"开始复习"按钮
5. 选择题：选择答案后提交，立即显示对错
6. 填空题：输入答案后点击"我答对了"或"我答错了"
7. 答对指定次数后自动移出错题本
8. 可使用批量提交功能

### 5. AI 讲解

1. 进入设置页面
2. 配置 DeepSeek API Key
3. 在答题页面点击"AI 讲解"按钮

## 常见问题

### Q: 端口被占用怎么办？
```bash
# 查找占用端口的进程（Windows）
Get-NetTCPConnection -LocalPort 8000

# 关闭进程
Stop-Process -Id <PID> -Force
```

### Q: 如何更新代码？
后端使用了 `--reload` 参数，代码修改后会自动重载。前端需要手动刷新浏览器。

### Q: 数据存储在哪里？
使用 SQLite 数据库，文件为 `test.db`，与项目文件在同一目录下。

### Q: 错题移除阈值是多少？
默认答对3次后自动移出错题本。

## License

MIT License
