from lnbits.db import Connection, Database, Filters, Page

from .models import PRSettings, RatingsFilters, RatingStats, Review

db = Database("ext_paidreviews")

############################# Settings #############################


async def create_settings(data: PRSettings) -> PRSettings:
    await db.insert("paidreviews.prsettings", data)
    return PRSettings(**data.dict())


async def update_settings(data: PRSettings) -> PRSettings:
    await db.update("paidreviews.prsettings", data)
    return PRSettings(**data.dict())


async def get_settings(user_id: str) -> PRSettings | None:
    return await db.fetchone(
        "SELECT * FROM paidreviews.prsettings WHERE user_id = :user_id",
        {"user_id": user_id},
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
    filters: Filters[RatingsFilters] | None = None,
    conn: Connection | None = None,
) -> Page[Review]:
    filters = filters or Filters()
    filters.sortby = filters.sortby or "created_at"
    return await (conn or db).fetch_page(
        query="SELECT * FROM paidreviews.reviews",
        where=["settings_id = :settings_id", "tag = :tag", "paid = :paid"],
        values={"settings_id": settings_id, "tag": tag, "paid": True},
        filters=filters,
        model=Review,
        table_name="paidreviews.reviews",
    )


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
    return row or RatingStats(review_count=0, avg_rating=0)


async def get_rating_stats_for_all_tags(settings_id: str) -> list[RatingStats]:
    return await db.fetchall(
        """
        SELECT tag, review_count, avg_rating
        FROM paidreviews.paidreviews_view_review_stats
        WHERE settings_id = :settings_id
        ORDER BY review_count DESC, tag ASC
        """,
        {"settings_id": settings_id},
        RatingStats,
    )


async def delete_review(review_id: str) -> None:
    await db.execute(
        "DELETE FROM paidreviews.reviews WHERE id = :id",
        {"id": review_id},
    )
