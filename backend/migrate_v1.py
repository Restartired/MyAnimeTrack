import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    conn = psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    cur = conn.cursor()
    
    try:
        print("Checking if cover_image_url column exists in Anime table...")
        # Check if column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='anime' AND column_name='cover_image_url';
        """)
        if cur.fetchone():
            print("Column header_image_url already exists.")
        else:
            print("Adding cover_image_url column...")
            cur.execute("""
                ALTER TABLE Anime
                ADD COLUMN cover_image_url TEXT;
            """)
            conn.commit()
            print("Migration successful.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
