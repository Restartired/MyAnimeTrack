from fastapi import FastAPI, HTTPException
from typing import List, Optional
import requests

from db import get_conn

from schemas import *
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="MyAnimeTrack API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# POST /anime（添加番剧）
@app.post("/anime", response_model=AnimeOut)
def create_anime(anime: AnimeCreate):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO Anime (title, start_date, total_episodes, source_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id, title, start_date, total_episodes, created_at, source_id
        """, (
            anime.title,
            anime.start_date,
            anime.total_episodes,
            anime.source_id
        ))
        
        row = cur.fetchone()
        new_anime_id = row[0]
        
        # Bangumi Episode Sync Logic
        if anime.source_id and anime.source_id.startswith("BGM-"):
            try:
                bgm_id = anime.source_id.split("-")[1]
                # Fetch episodes from Bangumi
                ep_response = requests.get(
                    f"https://api.bgm.tv/v0/episodes",
                    params={"subject_id": bgm_id},
                    headers={"User-Agent": "MyAnimeTrack/1.0"},
                    timeout=10
                )
                
                if ep_response.status_code == 200:
                    ep_data = ep_response.json()
                    episodes_to_insert = []
                    
                    for ep in ep_data.get("data", []):
                        # Map Bangumi type to system type
                        # 0: 本篇 -> main
                        # 1: SP -> sp
                        # 2: OP -> skip
                        # 3: ED -> skip
                        ep_type_val = ep.get("type")
                        if ep_type_val == 0:
                            ep_type = "main"
                            ep_code = f"E{ep.get('sort'):02d}" # Format as E01, E02...
                            # Handle case where sort might not be convertible to int directly or other formats
                            try:
                                ep_code = f"E{int(ep.get('sort')):02d}"
                            except:
                                ep_code = f"E{ep.get('sort')}"
                        elif ep_type_val == 1:
                            ep_type = "sp"
                            ep_code = f"SP{ep.get('sort')}"
                        else:
                            continue # Skip OP/ED/Trailer etc
                            
                        episodes_to_insert.append((
                            new_anime_id,
                            ep_code,
                            ep_type,
                            ep.get("sort"),
                            ep.get("name_cn") or ep.get("name"),
                            ep.get("airdate") or None
                        ))
                    
                    if episodes_to_insert:
                        cur.executemany("""
                            INSERT INTO Episode (
                                anime_id, episode_code, episode_type, display_order, title, air_date
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (anime_id, episode_code) DO NOTHING
                        """, episodes_to_insert)
            except Exception as e:
                print(f"Failed to sync episodes from Bangumi: {e}")
                # Don't fail the anime creation if sync fails
                pass

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

    return {
        "id": row[0],
        "title": row[1],
        "start_date": row[2],
        "total_episodes": row[3],
        "created_at": row[4],
        "source_id": row[5],
    }


# DELETE /anime/{anime_id}（删除番剧）
@app.delete("/anime/{anime_id}")
def delete_anime(anime_id: int):
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # 1. Delete Episode Reviews
        cur.execute("""
            DELETE FROM EpisodeReview
            WHERE episode_id IN (SELECT id FROM Episode WHERE anime_id = %s)
        """, (anime_id,))
        
        # 2. Delete Episodes
        cur.execute("DELETE FROM Episode WHERE anime_id = %s", (anime_id,))
        
        # 3. Delete Anime Reviews
        cur.execute("DELETE FROM AnimeReview WHERE anime_id = %s", (anime_id,))
        
        # 4. Delete Collection Links
        cur.execute("DELETE FROM CollectionAnime WHERE anime_id = %s", (anime_id,))
        
        # 5. Delete Anime
        cur.execute("DELETE FROM Anime WHERE id = %s", (anime_id,))
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Anime not found")
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
        
    return {"status": "ok"}


# GET /anime（查询番剧）
@app.get("/anime", response_model=List[AnimeOut])
def get_anime():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, start_date, total_episodes, created_at, source_id
        FROM Anime
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "title": r[1],
            "start_date": r[2],
            "total_episodes": r[3],
            "created_at": r[4],
            "source_id": r[5],
        }
        for r in rows
    ]


# POST /anime/{anime_id}/episodes（添加子集）
@app.post("/anime/{anime_id}/episodes")
def create_episode(anime_id: int, episode: EpisodeCreate):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO Episode (
            anime_id,
            episode_code,
            episode_type,
            display_order,
            title,
            air_date
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (anime_id, episode_code)
        DO NOTHING
    """, (
        anime_id,
        episode.episode_code,
        episode.episode_type,
        episode.display_order,
        episode.title,
        episode.air_date
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok"}


# GET /episode（按番剧查剧集）
@app.get("/anime/{anime_id}/episodes", response_model=list[EpisodeOut])
def get_episodes(anime_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT episode_code, episode_type, display_order, title, air_date
        FROM Episode
        WHERE anime_id = %s
        ORDER BY display_order
    """, (anime_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "episode_code": r[0],
            "episode_type": r[1],
            "display_order": r[2],
            "title": r[3],
            "air_date": r[4],
        }
        for r in rows
    ]


# DELETE /anime/{anime_id}/episodes/{episode_code}（删除子集）
@app.delete("/anime/{anime_id}/episodes/{episode_code}")
def delete_episode(anime_id: int, episode_code: str):
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Find episode ID
        cur.execute("SELECT id FROM Episode WHERE anime_id = %s AND episode_code = %s", (anime_id, episode_code))
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Episode not found")
            
        episode_id = row[0]
        
        # Delete reviews
        cur.execute("DELETE FROM EpisodeReview WHERE episode_id = %s", (episode_id,))
        
        # Delete episode
        cur.execute("DELETE FROM Episode WHERE id = %s", (episode_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
        
    return {"status": "ok"}


# POST /episode-review（写每话评价）
@app.post("/anime/{anime_id}/episodes/{episode_code}/review")
def create_episode_review(
    anime_id: int,
    episode_code: str,
    review: EpisodeReviewCreate
):
    conn = get_conn()
    cur = conn.cursor()

    # 通过业务身份查 episode_id
    cur.execute("""
        SELECT id
        FROM Episode
        WHERE anime_id = %s AND episode_code = %s
    """, (anime_id, episode_code))

    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return {"error": "Episode not found"}

    episode_id = row[0]

    # 写评价（UPSERT）
    cur.execute("""
        INSERT INTO EpisodeReview (episode_id, score, comment)
        VALUES (%s, %s, %s)
        ON CONFLICT (episode_id)
        DO UPDATE SET
            score = EXCLUDED.score,
            comment = EXCLUDED.comment,
            reviewed_at = CURRENT_TIMESTAMP
    """, (
        episode_id,
        review.score,
        review.comment
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok"}


# GET /anime/{anime_id}/episodes/{episode_code}/review（查子集评价）
@app.get("/anime/{anime_id}/episodes/{episode_code}/review",response_model=Optional[EpisodeReviewOut])
def get_episode_review(anime_id: int, episode_code: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT er.score, er.comment, er.reviewed_at
        FROM Episode e
        LEFT JOIN EpisodeReview er ON e.id = er.episode_id
        WHERE e.anime_id = %s AND e.episode_code = %s
    """, (anime_id, episode_code))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row or row[0] is None:
        return None

    return {
        "score": row[0],
        "comment": row[1],
        "reviewed_at": row[2],
    }


# POST /anime-review（写番剧评价）
@app.post("/anime/{anime_id}/review")
def create_anime_review(
    anime_id: int,
    review: AnimeReviewCreate
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO AnimeReview (anime_id, score, comment)
        VALUES (%s, %s, %s)
        ON CONFLICT (anime_id)
        DO UPDATE SET
            score = EXCLUDED.score,
            comment = EXCLUDED.comment,
            reviewed_at = CURRENT_TIMESTAMP
    """, (
        anime_id,
        review.score,
        review.comment
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok"}


# GET /anime/{anime_id}/review（按番剧评价）
@app.get("/anime/{anime_id}/review",response_model=Optional[AnimeReviewOut])
def get_anime_review(anime_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT score, comment, reviewed_at
        FROM AnimeReview
        WHERE anime_id = %s
    """, (anime_id,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "score": row[0],
        "comment": row[1],
        "reviewed_at": row[2],
    }


# POST /collections（创建收藏夹）
@app.post("/collections", response_model=CollectionOut)
def create_collection(collection: CollectionCreate):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO Collection (name, description)
        VALUES (%s, %s)
        RETURNING id, name, description, created_at
    """, (
        collection.name,
        collection.description
    ))

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "created_at": row[3],
    }


# DELETE /collections/{collection_id}（删除收藏夹）
@app.delete("/collections/{collection_id}")
def delete_collection(collection_id: int):
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Delete relationships first
        cur.execute("DELETE FROM CollectionAnime WHERE collection_id = %s", (collection_id,))
        
        # Delete collection
        cur.execute("DELETE FROM Collection WHERE id = %s", (collection_id,))
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Collection not found")
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
        
    return {"status": "ok"}


# GET /collections（获取收藏夹列表）
@app.get("/collections", response_model=list[CollectionOut])
def get_collections():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, description, created_at
        FROM Collection
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "created_at": r[3],
        }
        for r in rows
    ]


# POST /collections/{collection_id}/anime（收藏夹添加动漫）
@app.post("/collections/{collection_id}/anime")
def add_anime_to_collection(
    collection_id: int,
    data: CollectionAnimeCreate
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO CollectionAnime (collection_id, anime_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (
        collection_id,
        data.anime_id
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok"}


# GET /collections/{collection_id}/anime（收藏夹的动漫列表）
@app.get("/collections/{collection_id}/anime", response_model=list[AnimeOut])
def get_collection_anime(collection_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT a.id, a.title, a.start_date, a.total_episodes, a.created_at, a.source_id
        FROM Anime a
        JOIN CollectionAnime ca ON a.id = ca.anime_id
        WHERE ca.collection_id = %s
        ORDER BY a.created_at DESC
    """, (collection_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "title": r[1],
            "start_date": r[2],
            "total_episodes": r[3],
            "created_at": r[4],
            "source_id": r[5],
        }
        for r in rows
    ]


# GET /bangumi/search（搜索 Bangumi）
@app.get("/bangumi/search", response_model=dict)
def search_bangumi(query: str):
    """搜索 Bangumi 番剧"""
    try:
        # Bangumi 搜索 API
        search_response = requests.get(
            f"https://api.bgm.tv/search/subject/{query}",
            params={"type": 2, "responseGroup": "large"},  # type=2 表示动画
            headers={"User-Agent": "MyAnimeTrack/1.0 (https://github.com/yourusername/MyAnimeTrack)"},
            timeout=10
        )
        search_response.raise_for_status()
        search_data = search_response.json()
        
        # 格式化搜索结果
        results = []
        for item in search_data.get("list", [])[:10]:  # 最多返回10个结果
            # 获取详细信息
            subject_id = item.get("id")
            if subject_id:
                try:
                    detail_response = requests.get(
                        f"https://api.bgm.tv/v0/subjects/{subject_id}",
                        headers={"User-Agent": "MyAnimeTrack/1.0"},
                        timeout=10
                    )
                    detail_response.raise_for_status()
                    detail_data = detail_response.json()
                    
                    # 提取开播日期
                    start_date = detail_data.get("date")
                    if start_date and len(start_date) >= 10:
                        start_date = start_date[:10]  # 只取日期部分
                    else:
                        start_date = None
                    
                    # 提取总集数
                    total_episodes = detail_data.get("eps") or detail_data.get("total_episodes")
                    
                    # 提取封面图片
                    images = detail_data.get("images", {})
                    cover_image = images.get("large") or images.get("common") or images.get("medium")
                    
                    results.append({
                        "id": subject_id,
                        "title": detail_data.get("name_cn") or detail_data.get("name"),
                        "name_jp": detail_data.get("name"),
                        "name_cn": detail_data.get("name_cn"),
                        "start_date": start_date,
                        "total_episodes": total_episodes,
                        "cover_image": cover_image,
                        "summary": detail_data.get("summary", ""),
                        "source_id": f"BGM-{subject_id}"
                    })
                except Exception as e:
                    # 如果获取详情失败，使用搜索结果中的基本信息
                    images = item.get("images", {}) if item.get("images") else {}
                    cover_image = images.get("large") or images.get("common") if images else None
                    results.append({
                        "id": subject_id,
                        "title": item.get("name_cn") or item.get("name"),
                        "name_jp": item.get("name"),
                        "name_cn": item.get("name_cn"),
                        "start_date": None,
                        "total_episodes": item.get("eps"),
                        "cover_image": cover_image,
                        "summary": item.get("summary", ""),
                        "source_id": f"BGM-{subject_id}"
                    })
                    continue
        
        return {"results": results}
    except requests.Timeout:
        return {"error": "请求超时，请稍后重试", "results": []}
    except requests.RequestException as e:
        return {"error": f"Bangumi API 错误: {str(e)}", "results": []}
    except Exception as e:
        return {"error": f"搜索失败: {str(e)}", "results": []}
