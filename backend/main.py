from fastapi import FastAPI
from typing import List

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
    conn.commit()

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


