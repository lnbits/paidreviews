from lnbits.db import Database

from .models import PRSettings, RatingStats, Review

db = Database("ext_paidreviews")

############################# Settings #############################


async def create_settings(data: PRSettings) -> PRSettings:
    await db.insert("paidreviews.prsettings", data)
    return PRSettings(**data.dict())


async def update_settings(data: PRSettings) -> PRSettings:
    await db.update("paidreviews.prsettings", data)
    return PRSettings(**data.dict())


async def get_settings(user: str) -> PRSettings | None:
    return await db.fetchone(
        "SELECT * FROM paidreviews.prsettings WHERE user = :user",
        {"user": user},
        PRSettings,
    )


async def get_settings_from_id(settings_id: str) -> PRSettings | None:
    return await db.fetchone(
        "SELECT * FROM paidreviews.prsettings WHERE id = :id",
        {"id": settings_id},
        PRSettings,
    )


############################# Reviews #############################


async def create_review(data: Review) -> Review:
    await db.insert("paidreviews.reviews", data)
    return data


async def get_reviews(settings_id: str | list[str]) -> list[Review]:
    return await db.fetchall(
        "SELECT * FROM paidreviews.reviews "
        "WHERE settings_id = :settings_id AND paid = :paid "
        "ORDER BY CAST(created_at AS INTEGER) DESC",
        {"settings_id": settings_id, "paid": True},
        model=Review,
    )


async def get_review(review_id: str) -> Review | None:
    return await db.fetchone(
        "SELECT * FROM paidreviews.reviews WHERE id = :id",
        {"id": review_id},
        Review,
    )


async def get_review_by_hash(payment_hash: str) -> Review | None:
    return await db.fetchone(
        "SELECT * FROM paidreviews.reviews WHERE payment_hash = :payment_hash",
        {"payment_hash": payment_hash},
        Review,
    )


async def get_reviews_by_tag(
    settings_id: str,
    tag: str,
    *,
    limit: int,
    before_created_at: int | None = None,
) -> list[Review]:
    params = {
        "settings_id": settings_id,
        "tag": tag,
        "paid": True,
        "limit": limit,
    }

    if before_created_at is not None:
        params["before_created_at"] = int(before_created_at)
        sql = """
            SELECT *
            FROM paidreviews.reviews
            WHERE settings_id = :settings_id
              AND tag = :tag
              AND paid = :paid
              AND CAST(created_at AS INTEGER) < :before_created_at
            ORDER BY CAST(created_at AS INTEGER) DESC
            LIMIT :limit
        """
    else:
        sql = """
            SELECT *
            FROM paidreviews.reviews
            WHERE settings_id = :settings_id
              AND tag = :tag
              AND paid = :paid
            ORDER BY CAST(created_at AS INTEGER) DESC
            LIMIT :limit
        """

    return await db.fetchall(sql, params, model=Review)


async def update_review(data: Review) -> Review:
    await db.update("paidreviews.reviews", data)
    return data


async def get_rating_stats(settings_id: str, tag: str) -> RatingStats:
    """
    Return aggregate stats (count + average) for paid reviews of a settings_id/tag.
    Backed by the paidreviews_view_review_stats DB view.
    """
    row = await db.fetchone(
        """
        SELECT review_count, avg_rating
        FROM paidreviews.paidreviews_view_review_stats
        WHERE settings_id = :settings_id AND tag = :tag
        """,
        {"settings_id": settings_id, "tag": tag},
        RatingStats,  # let the DB wrapper hydrate the model
    )
    return row or RatingStats(review_count=0, avg_rating=0.0)


async def delete_review(review_id: str) -> None:
    await db.execute(
        "DELETE FROM paidreviews.reviews WHERE id = :id",
        {"id": review_id},
    )
