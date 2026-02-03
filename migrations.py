async def m001_settings(db):
    """
    Initial settings table.
    """
    await db.execute(
        """
        CREATE TABLE paidreviews.prsettings (
            id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            cost INTEGER DEFAULT 0,
            wallet TEXT NOT NULL DEFAULT '',
            user_id TEXT NOT NULL UNIQUE,
            comment_word_limit INTEGER DEFAULT 0,
            tags TEXT NOT NULL DEFAULT ''
        );
    """
    )


async def m002_reviews(db):
    """
    Initial reviews table.
    """
    await db.execute(
        f"""
        CREATE TABLE paidreviews.reviews (
            id TEXT PRIMARY KEY NOT NULL,
            settings_id TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            tag TEXT NOT NULL DEFAULT '',
            rating INTEGER DEFAULT 0,
            comment TEXT NOT NULL DEFAULT '',
            paid BOOLEAN DEFAULT FALSE,
            payment_hash TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )


async def m003_average(db):
    """
    Create a view to hold aggregated review stats (count + avg).
    """
    if db.type in {"POSTGRES", "COCKROACH"}:
        await db.execute(
            """
            CREATE OR REPLACE VIEW paidreviews.paidreviews_view_review_stats AS
            SELECT
              settings_id,
              tag,
              COUNT(*) AS review_count,
              AVG(CAST(rating AS REAL)) AS avg_rating
            FROM paidreviews.reviews
            WHERE paid = TRUE
            GROUP BY settings_id, tag;
            """
        )
    elif db.type == "SQLITE":
        await db.execute(
            """
            CREATE VIEW IF NOT EXISTS paidreviews.paidreviews_view_review_stats AS
            SELECT
              settings_id,
              tag,
              COUNT(*) AS review_count,
              AVG(CAST(rating AS REAL)) AS avg_rating
            FROM reviews
            WHERE paid = 1
            GROUP BY settings_id, tag;
            """
        )
