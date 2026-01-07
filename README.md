# MyAnimeTrack

一个基于 FastAPI + Nuxt 3 + PostgreSQL 的个人番剧追踪/管理系统。这是一个新手练手项目。

## 简介

MyAnimeTrack 允许你管理你的番剧观看进度，支持从 Bangumi 导入数据（包括批量导入收藏夹），并提供评分、评价、收藏夹管理等功能。

**AI 创作声明**: 本项目代码由 AI 辅助完成，特别感谢：
- **ChatGPT**
- **Cursor Auto**
- **Antigravity Gemini 3Pro (High)**

## 功能特性

- **番剧管理**: 添加、删除、查看番剧详情。
- **Bangumi 集成**:
  - 支持通过 URL 或 ID 导入番剧。
  - **批量导入**: 支持导入 Bangumi 个人收藏夹，自动同步评分和评价。
  - **自动同步**: 同步 OP/ED/PV 等剧集信息，以及封面图。
- **进度追踪**: 标记剧集观看状态（通过评分/评论）。
- **评分系统**: 个人评分与详细评价。
- **收藏夹**: 自定义收藏夹分类管理。

## 运行环境

- **Python**: 3.8+
- **Node.js**: 16+ (推荐使用 pnpm)
- **PostgreSQL**: 13+

## 启动指南

### 1. 数据库设置

首先创建一个名为 `myanimetrack` 的 PostgreSQL 数据库。

```sql
CREATE DATABASE myanimetrack;
```

然后执行以下 SQL 语句创建数据表：

```sql
-- 番剧表
CREATE TABLE Anime (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    start_date DATE,
    total_episodes INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_id VARCHAR(100),
    cover_image_url TEXT
);

-- 剧集表
CREATE TABLE Episode (
    id SERIAL PRIMARY KEY,
    anime_id INT NOT NULL REFERENCES Anime(id),
    episode_code VARCHAR(255) NOT NULL,
    episode_type VARCHAR(255) NOT NULL,
    display_order INT NOT NULL,
    title VARCHAR(255),
    air_date DATE,
    UNIQUE (anime_id, episode_code)
);

-- 剧集评价
CREATE TABLE EpisodeReview (
    id SERIAL PRIMARY KEY,
    episode_id INT NOT NULL REFERENCES Episode(id),
    score INT CHECK (score >=0 AND score <=10),
    comment TEXT,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (episode_id)
);

-- 番剧总评
CREATE TABLE AnimeReview (
    id SERIAL PRIMARY KEY,
    anime_id INT NOT NULL REFERENCES Anime(id),
    score INT CHECK (score >=0 AND score <=10),
    comment TEXT,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (anime_id)
);

-- 收藏夹
CREATE TABLE Collection (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 收藏夹-番剧关联表（多对多）
CREATE TABLE CollectionAnime (
    collection_id INT REFERENCES Collection(id),
    anime_id INT REFERENCES Anime(id),
    PRIMARY KEY (collection_id, anime_id)
);
```

### 2. 后端 (Backend)

1.  进入后端目录：
    ```bash
    cd backend
    ```

2.  创建并激活虚拟环境（可选）：
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    # .venv\Scripts\activate   # Windows
    ```

3.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

4.  配置环境变量：
    复制 `.env.example` 为 `.env`，并修改数据库配置：
    ```bash
    cp .env.example .env
    ```
    修改 `.env` 中的 `DB_PASSWORD` 等字段。

5.  启动服务：
    ```bash
    uvicorn main:app --reload
    ```
    服务默认运行在 `http://127.0.0.1:8000`。

### 3. 前端 (Frontend)

1.  进入前端目录：
    ```bash
    cd frontend
    ```

2.  安装依赖：
    ```bash
    pnpm install
    ```

3.  启动开发服务器：
    ```bash
    pnpm dev
    ```
    服务默认运行在 `http://localhost:3000`。
