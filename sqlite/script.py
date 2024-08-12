import sqlite3


def init_db():
    conn = sqlite3.connect('lightnovel.db')
    cursor = conn.cursor()
    create_table_script = """
    CREATE TABLE IF NOT EXISTS "book" (
      "id" text NOT NULL,
      "book_id" text NOT NULL,
      "source" text NOT NULL,
      "book_name" text,
      "author" text,
      "tags" text,
      "describe" text,
      "cover_url" text,
      PRIMARY KEY ("id")
    );
    
    CREATE INDEX IF NOT EXISTS "idx_book" ON "book" (
      "book_id" COLLATE BINARY ASC,
      "source" COLLATE BINARY ASC
    );
    
    CREATE TABLE IF NOT EXISTS "chapter" (
      "id" text NOT NULL,
      "book_table_id" text NOT NULL,
      "chapter_id" text NOT NULL,
      "chapter_name" text,
      "chapter_order" integer NOT NULL,
      "content" text,
      "last_update_time" integer,
      "purchase_fail_flag" integer,
      PRIMARY KEY ("id")
    );
    
    CREATE INDEX IF NOT EXISTS "idx_chapter" ON "chapter" (
      "book_table_id" COLLATE BINARY ASC
    );
    
    CREATE TABLE IF NOT EXISTS "cookie" (
      "id" text NOT NULL,
      "source" text NOT NULL,
      "cookie" text,
      "token" text,
      "uid" text,
      PRIMARY KEY ("id")
    );
    
    CREATE TABLE IF NOT EXISTS "pic" (
      "id" text NOT NULL,
      "chapter_table_id" text NOT NULL,
      "pic_url" text NOT NULL,
      "pic_path" text,
      "pic_id" text,
      PRIMARY KEY ("id")
    );
    
    CREATE INDEX IF NOT EXISTS "idx_pic" ON "pic" (
      "chapter_table_id" COLLATE BINARY ASC
    );
    """
    cursor.executescript(create_table_script)
    conn.commit()
    conn.close()