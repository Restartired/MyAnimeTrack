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

def sync_bangumi_data(anime_id: int, source_id: str, cur):
    """
    Helper function to sync anime details and episodes from Bangumi.
    """
    if not source_id or not source_id.startswith("BGM-"):
        return

    try:
        bgm_id = source_id.split("-")[1]
        
        # 1. Fetch Subject Detail for Cover Image (Update only if missing or force sync)
        try:
            subject_resp = requests.get(
                f"https://api.bgm.tv/v0/subjects/{bgm_id}",
                headers={"User-Agent": "MyAnimeTrack/1.0"},
                timeout=5
            )
            if subject_resp.status_code == 200:
                subj_data = subject_resp.json()
                images = subj_data.get("images", {})
                cover_url = images.get("large") or images.get("common") or images.get("medium")
                
                # Update cover image (always update on sync)
                if cover_url:
                    cur.execute("""
                        UPDATE Anime SET cover_image_url = %s WHERE id = %s
                    """, (cover_url, anime_id))
        except Exception as e:
            print(f"Failed to fetch cover image: {e}")

        # 2. Fetch episodes from Bangumi
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
                # 2: OP -> op
                # 3: ED -> ed
                # Other -> trailer/other
                ep_type_val = ep.get("type")
                if ep_type_val == 0:
                    ep_type = "main"
                    sort_val = ep.get('sort')
                    try:
                        ep_code = f"E{int(float(sort_val)):02d}"
                    except:
                        ep_code = f"E{sort_val}"
                elif ep_type_val == 1:
                    ep_type = "sp"
                    ep_code = f"SP{ep.get('sort')}"
                elif ep_type_val == 2:
                    ep_type = "op"
                    ep_code = f"OP{ep.get('sort')}"
                elif ep_type_val == 3:
                    ep_type = "ed"
                    ep_code = f"ED{ep.get('sort')}"
                else:
                    ep_type = "other"
                    ep_code = f"O{ep.get('sort')}"
                    
                episodes_to_insert.append((
                    anime_id,
                    ep_code,
                    ep_type,
                    0, # display_order not used anymore for sorting
                    ep.get("name_cn") or ep.get("name"),
                    ep.get("airdate") or None
                ))
            
            if episodes_to_insert:
                # Use UPSERT to update existing episodes or insert new ones
                # Conflict on (anime_id, episode_code)
                cur.executemany("""
                    INSERT INTO Episode (
                        anime_id, episode_code, episode_type, display_order, title, air_date
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (anime_id, episode_code) 
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        air_date = EXCLUDED.air_date
                """, episodes_to_insert)
    except Exception as e:
        print(f"Failed to sync episodes from Bangumi: {e}")
        pass


# POST /anime（添加番剧）
@app.post("/anime", response_model=AnimeOut)
def create_anime(anime: AnimeCreate):
    conn = get_conn()
    cur = conn.cursor()

    try:
        # Check if exists if source_id is provided
        if anime.source_id:
            cur.execute("SELECT id FROM Anime WHERE source_id = %s", (anime.source_id,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail=f"Anime with source_id {anime.source_id} already exists")

        cur.execute("""
            INSERT INTO Anime (title, start_date, total_episodes, source_id, cover_image_url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, title, start_date, total_episodes, created_at, source_id, cover_image_url
        """, (
            anime.title,
            anime.start_date,
            anime.total_episodes,
            anime.source_id,
            anime.cover_image_url
        ))
        
        row = cur.fetchone()
        new_anime_id = row[0]
        
        # Bangumi Episode Sync Logic (Refactored)
        if anime.source_id and anime.source_id.startswith("BGM-"):
            sync_bangumi_data(new_anime_id, anime.source_id, cur)

        conn.commit()
        
        # Retrieve final state (incase sync updated cover)
        cur.execute("SELECT id, title, start_date, total_episodes, created_at, source_id, cover_image_url FROM Anime WHERE id = %s", (new_anime_id,))
        final_row = cur.fetchone()
        
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

    return {
        "id": final_row[0],
        "title": final_row[1],
        "start_date": final_row[2],
        "total_episodes": final_row[3],
        "created_at": final_row[4],
        "source_id": final_row[5],
        "cover_image_url": final_row[6]
    }


# POST /anime/check_import（检查导入）
@app.post("/anime/check_import")
def check_import(data: dict):
    url_or_id = data.get("url_or_id")
    if not url_or_id:
        return {"error": "Missing input"}
        
    # Extract Bangumi ID
    bgm_id = None
    if "bangumi.tv/subject/" in url_or_id:
        try:
            bgm_id = url_or_id.split("subject/")[1].split("/")[0].split("?")[0]
        except:
             return {"error": "Invalid URL format"}
    elif url_or_id.isdigit():
        bgm_id = url_or_id
        
    if not bgm_id:
        return {"error": "Could not parse Bangumi ID"}
        
    source_id = f"BGM-{bgm_id}"
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM Anime WHERE source_id = %s", (source_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        return {
            "exists": True,
            "id": row[0],
            "title": row[1],
            "source_id": source_id
        }
    
    # Check if valid on Bangumi
    try:
        resp = requests.get(f"https://api.bgm.tv/v0/subjects/{bgm_id}", headers={"User-Agent": "MyAnimeTrack/1.0"})
        if resp.status_code == 404:
             return {"exists": False, "valid": False, "error": "Bangumi ID not found"}
        data = resp.json()
        
        images = data.get("images", {})
        cover_image = images.get("large") or images.get("common")
        
        return {
            "exists": False,
            "valid": True,
            "source_id": source_id,
            "title": data.get("name_cn") or data.get("name"),
            "start_date": data.get("date"),
            "total_episodes": data.get("eps") or data.get("total_episodes"),
            "cover_image_url": cover_image
        }
    except:
        return {"exists": False, "valid": False, "error": "Bangumi API Error"}


# POST /bangumi/import_collection（批量导入）
@app.post("/bangumi/import_collection")
def import_collection(data: dict):
    url = data.get("url")
    if not url:
        return {"error": "Missing URL"}
        
    # Parse URL: http://bangumi.tv/anime/list/{username}/{type}
    try:
        parts = url.replace("https://", "").replace("http://", "").split("/")
        # format: bangumi.tv / anime / list / {username} / {type}
        if len(parts) < 5 or parts[1] != "anime" or parts[2] != "list":
             return {"error": "Invalid Collection URL format. Expected: bangumi.tv/anime/list/{username}/{type}"}
        
        username = parts[3]
        type_str = parts[4].split("?")[0]
        
        type_map = {
            "wish": 1,
            "collect": 2,
            "do": 3,
            "on_hold": 4,
            "dropped": 5
        }
        
        collection_type = type_map.get(type_str)
        if not collection_type:
            # Maybe it's not a type needed to be mapped? Use correct type or default to 2 (collect)?
            # But the user specified URL format.
             return {"error": f"Unknown collection type: {type_str}"}
             
    except Exception as e:
        return {"error": f"Failed to parse URL: {e}"}

    # Fetch User Collection
    try:
        # Fetching first 50 items for now. 
        # Ideally should loop with offset until empty, but let's start safe.
        limit = 50
        offset = 0
        added_count = 0
        updated_count = 0
        failed_count = 0
        
        conn = get_conn()
        cur = conn.cursor()
        
        # We might need to pagination loop here
        # For this iteration, let's just do one page or two.
        
        while True:
            resp = requests.get(
                f"https://api.bgm.tv/v0/users/{username}/collections",
                params={
                    "subject_type": 2, # Anime
                    "type": collection_type,
                    "limit": limit,
                    "offset": offset
                },
                headers={"User-Agent": "MyAnimeTrack/1.0"},
                timeout=15
            )
            
            if resp.status_code != 200:
                break
                
            data = resp.json()
            items = data.get("data", [])
            if not items:
                break
                
            for item in items:
                try:
                    subject = item.get("subject")
                    if not subject:
                        continue
                        
                    bgm_id = subject.get("id")
                    source_id = f"BGM-{bgm_id}"
                    
                    # Extract Rating and Comment
                    imported_score = item.get("rate")
                    imported_comment = item.get("comment")
                    if imported_comment and not imported_comment.strip():
                        imported_comment = None
                    
                    # Check DB
                    cur.execute("SELECT id FROM Anime WHERE source_id = %s", (source_id,))
                    row = cur.fetchone()
                    
                    anime_id = None
                    if row:
                        # EXISTS -> Update
                        anime_id = row[0]
                        sync_bangumi_data(anime_id, source_id, cur)
                        updated_count += 1
                    else:
                        # NEW -> Insert
                        title = subject.get("name_cn") or subject.get("name")
                        start_date = subject.get("date")
                        # Truncate date if needed
                        if start_date and len(start_date) > 10: start_date = start_date[:10]
                        
                        eps = subject.get("eps") or subject.get("total_episodes")
                        
                        images = subject.get("images", {})
                        cover = images.get("large") or images.get("common")
                        
                        cur.execute("""
                            INSERT INTO Anime (title, start_date, total_episodes, source_id, cover_image_url)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING id
                        """, (title, start_date, eps, source_id, cover))
                        
                        anime_id = cur.fetchone()[0]
                        sync_bangumi_data(anime_id, source_id, cur)
                        added_count += 1
                    
                    # Handle ReviewSync (Do not overwrite valid local data)
                    if anime_id and (imported_score or imported_comment):
                        cur.execute("SELECT score, comment FROM AnimeReview WHERE anime_id = %s", (anime_id,))
                        review_row = cur.fetchone()
                        
                        if not review_row:
                            # No review exists, safe to insert both
                            cur.execute("""
                                INSERT INTO AnimeReview (anime_id, score, comment)
                                VALUES (%s, %s, %s)
                            """, (anime_id, imported_score, imported_comment))
                        else:
                            # Review exists, check what is missing
                            local_score, local_comment = review_row
                            
                            new_score = local_score if (local_score is not None and local_score > 0) else imported_score
                            new_comment = local_comment if (local_comment and local_comment.strip()) else imported_comment
                            
                            # Update if we have something new to add (and it's different)
                            if (new_score != local_score) or (new_comment != local_comment):
                                cur.execute("""
                                    UPDATE AnimeReview 
                                    SET score = %s, comment = %s
                                    WHERE anime_id = %s
                                """, (new_score, new_comment, anime_id))

                except Exception as e:
                    print(f"Error importing item: {e}")
                    failed_count += 1
                    
            offset += limit
            if offset >= data.get("total", 0) or offset > 200: # Safety break at 200
                break
                
        conn.commit()
        cur.close()
        conn.close()
        
        return {
            "status": "ok",
            "added": added_count,
            "updated": updated_count,
            "failed": failed_count,
            "message": f"Successfully imported: {added_count} added, {updated_count} updated."
        }
        
    except Exception as e:
        return {"error": f"Import failed: {e}"}


# POST /anime/{id}/sync（原地更新）
@app.post("/anime/{anime_id}/sync")
def sync_anime(anime_id: int):
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT source_id FROM Anime WHERE id = %s", (anime_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Anime has no source_id to sync from")
        
    source_id = row[0]
    
    try:
        sync_bangumi_data(anime_id, source_id, cur)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
        
    return {"status": "ok"}


# DELETE /anime/{anime_id}（删除番剧）
@app.delete("/anime/{anime_id}")
def delete_anime(anime_id: int):
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            DELETE FROM EpisodeReview
            WHERE episode_id IN (SELECT id FROM Episode WHERE anime_id = %s)
        """, (anime_id,))
        cur.execute("DELETE FROM Episode WHERE anime_id = %s", (anime_id,))
        cur.execute("DELETE FROM AnimeReview WHERE anime_id = %s", (anime_id,))
        cur.execute("DELETE FROM CollectionAnime WHERE anime_id = %s", (anime_id,))
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
        SELECT a.id, a.title, a.start_date, a.total_episodes, a.created_at, a.source_id, a.cover_image_url, ar.score
        FROM Anime a
        LEFT JOIN AnimeReview ar ON a.id = ar.anime_id
        ORDER BY a.created_at DESC
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
            "cover_image_url": r[6],
            "my_score": r[7]
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

    # Sort by Air Date, then fallback to parsing number from code if possible, or string sort
    cur.execute("""
        SELECT episode_code, episode_type, display_order, title, air_date
        FROM Episode
        WHERE anime_id = %s
        ORDER BY 
            CASE 
                WHEN episode_type = 'main' THEN 0 
                WHEN episode_type = 'sp' THEN 2 
                WHEN episode_type = 'ova' THEN 3
                ELSE 1 
            END,
            air_date NULLS LAST, 
            episode_code
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
        cur.execute("SELECT id FROM Episode WHERE anime_id = %s AND episode_code = %s", (anime_id, episode_code))
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Episode not found")
            
        episode_id = row[0]
        cur.execute("DELETE FROM EpisodeReview WHERE episode_id = %s", (episode_id,))
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


# PUT /collections/{collection_id}（更新收藏夹）
@app.put("/collections/{collection_id}", response_model=CollectionOut)
def update_collection(collection_id: int, collection: CollectionCreate):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE Collection
            SET name = %s, description = %s
            WHERE id = %s
            RETURNING id, name, description, created_at
        """, (
            collection.name,
            collection.description,
            collection_id
        ))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Collection not found")
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
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
        SELECT a.id, a.title, a.start_date, a.total_episodes, a.created_at, a.source_id, a.cover_image_url
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
            "cover_image_url": r[6],
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


# DELETE /collections/{collection_id}/anime/{anime_id}（从收藏夹移除动漫）
@app.delete("/collections/{collection_id}/anime/{anime_id}")
def remove_anime_from_collection(collection_id: int, anime_id: int):
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            DELETE FROM CollectionAnime 
            WHERE collection_id = %s AND anime_id = %s
        """, (collection_id, anime_id))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
        
    return {"status": "ok"}
