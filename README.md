# Facebook Marketplace Bot

根据 `csvs/items.csv` 自动在 Facebook Marketplace 发布 **Item** 类商品。浏览器使用 [CloakBrowser](https://github.com/CloakHQ/cloakbrowser)（隐身 Chromium + Playwright API），登录通过 `fb.json` Cookie，并可复用 `profiles/facebook` 会话。

> 请遵守 Facebook 服务条款。自动化发帖存在账号风控风险，仅建议用于自己账号、合理频率的场景。

## 功能

- 从 CSV 批量发布 Item 商品（标题、图片、价格、分类、成色、描述、地点等）
- Cookie 登录（`fb.json`）；已有 profile 时跳过重复注入 Cookie
- Cookie 登录失败时自动删除 `profiles/facebook`，下次干净启动
- 图片路径支持相对项目根目录（如 `images`）
- 成色（Condition）用键盘方向键选择，避免伪类遮挡点击
- 页面元素找不到时自动重试 2 次，仍失败则跳过，不直接退出程序

## 技术栈

- Python 3
- [CloakBrowser](https://pypi.org/project/cloakbrowser/)（Playwright 兼容 API）

## 目录结构

```
facebook-marketplace-bot-master/
├── main.py                 # 入口
├── requirements.txt
├── fb.json                 # Facebook Cookie（需自备，勿提交）
├── csvs/
│   └── items.csv           # 商品数据
├── images/                 # 示例图片目录（相对路径）
├── profiles/               # 浏览器持久配置（自动生成）
└── helpers/
    ├── scraper.py          # 浏览器 / 登录 / 元素操作
    ├── listing_helper.py   # 发布流程
    └── csv_helper.py       # 读取 CSV
```

## 安装

1. 安装 [Python](https://www.python.org/downloads/) 3.10+
2. 安装依赖：

```bash
pip install -r requirements.txt
```

首次运行会自动下载 CloakBrowser 的 Chromium 二进制（约 200MB）。

3. （可选）获取更新的 stealth 浏览器：

```bash
python -m cloakbrowser login
```

## 配置

### 1. Cookie：`fb.json`

将 Facebook 登录 Cookie 导出为 JSON（Chrome 扩展常见格式），放到项目根目录，命名为 `fb.json`。

至少应包含可用的会话 Cookie（如 `c_user`、`xs` 等）。过期后需重新导出。

### 2. 商品：`csvs/items.csv`

| 列 | 说明 |
|----|------|
| Title | 标题 |
| Photos Folder | 图片文件夹，相对项目根目录，如 `images` |
| Photos Names | 文件名，多个用 `;` 分隔，如 `1.png; 2.png` |
| Price | 价格 |
| Category | 分类，须与页面选项文案一致，如 `Sports & Outdoors` |
| Condition | 成色，见下方可选值 |
| Brand | 预留列（当前发布逻辑可不依赖） |
| Description | 描述 |
| Location | 地点，发布时会选下拉第一项 |
| Groups | 预留；当前默认发布流程未强制发帖到小组 |

**Condition 可选值（须与下列一致，大小写不敏感）：**

- `New`
- `Used - Like New`
- `Used - Good`
- `Used - Fair`

示例：

```csv
"Title","Photos Folder","Photos Names","Price","Category","Condition","Brand","Description","Location","Groups"
"Fitness Equipment","images","1.png; 2.png","20","Sports & Outdoors","Used - Good","Example Brand","This is example description","London, United Kingdom","Group name 1"
```

### 3. 代理（国内网络常需）

若无法打开 Facebook：

```bat
set PROXY_URL=http://127.0.0.1:7890
python main.py
```

也支持 `HTTP_PROXY` / `HTTPS_PROXY`。

## 运行

在项目根目录执行：

```bash
python main.py
```

流程概要：

1. 启动 CloakBrowser，使用 `profiles/facebook`
2. 打开 Marketplace；有有效 profile 则直接登录，否则注入 `fb.json`
3. 读取 `csvs/items.csv`，逐条打开发布页并填写、发布

## 登录与 Profile 说明

| 情况 | 行为 |
|------|------|
| `profiles/facebook` 已存在且仍登录 | 不重新注入 Cookie |
| 无 profile / 会话失效 | 从 `fb.json` 注入 Cookie |
| Cookie 登录仍失败 | 删除 `profiles/facebook` 并退出，请更新 Cookie 后重跑 |

## 注意事项

- 浏览器界面语言按英文（`en-US`）启动；选择器依赖英文文案
- Category / Condition / Location 等文案须与 Facebook 页面一致
- `fb.json`、`profiles/` 含登录态，勿提交到公开仓库（已在 `.gitignore` 中忽略）
- Facebook 页面改版可能导致选择器失效，需同步改 `helpers/listing_helper.py`

## License

见仓库内 `LICENSE` 文件。
