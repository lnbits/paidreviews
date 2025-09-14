from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from lnbits.core.models import WalletTypeInfo
from lnbits.core.services import create_invoice
from lnbits.decorators import require_admin_key
from loguru import logger

from .crud import (
    create_review,
    create_settings,
    delete_review,
    get_rating_stats,
    get_rating_stats_for_all_tags,
    get_review,
    get_reviews_by_tag,
    get_settings,
    get_settings_from_id,
    update_settings,
)
from .models import (
    CreatePrSettings,
    KeysetPage,
    PostReview,
    PRSettings,
    RatingStats,
    Review,
)

paidreviews_api_router = APIRouter()

############################# Settings #############################


@paidreviews_api_router.get("/api/v1/settings")
async def api_settings(
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> PRSettings:
    pr_settings = await get_settings(wallet.wallet.user)
    if not pr_settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Update the settings."
        )
    return pr_settings


@paidreviews_api_router.post("/api/v1/settings")
async def api_create_settings(
    data: CreatePrSettings,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> PRSettings:
    settings = PRSettings(**data.dict())
    settings.user = wallet.wallet.user
    settings = await create_settings(settings)
    return settings


@paidreviews_api_router.put("/api/v1/settings/{settings_id}")
async def api_update_settings(
    settings_id: str,
    data: CreatePrSettings,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> PRSettings:
    settings = await get_settings_from_id(settings_id)
    if not settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Settings do not exist."
        )

    if settings.user != wallet.wallet.user:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your reviews."
        )

    for field, value in data.dict().items():
        if value is not None:
            setattr(settings, field, value)

    settings = await update_settings(settings)
    return settings


############################## Tags #############################


@paidreviews_api_router.get("/api/v1/tags/{settings_id}")
async def api_get_tags(response: Response, settings_id: str) -> list[RatingStats]:
    tags = await get_rating_stats_for_all_tags(settings_id)
    response.headers["Cache-Control"] = "public, max-age=30"
    return tags


############################# Reviews #############################

## TO DO:
## Add pagination to the reviews endpoint
## Delete unpaid reviiews after a certain time period


@paidreviews_api_router.get("/api/v1/{settings_id}/{tag}")
async def api_reviews_by_tag(
    response: Response,
    settings_id: str,
    tag: str,
    limit: int = Query(
        ..., ge=1, le=50, description="Number of reviews to return (1-50)."
    ),
    before: int | None = Query(
        None, description="Return items with created_at < this unix timestamp."
    ),
) -> KeysetPage:
    items = await get_reviews_by_tag(
        settings_id=settings_id,
        tag=tag,
        limit=limit,
        before_created_at=before,
    )

    next_cursor = None
    if items and len(items) == limit and items[-1].created_at:
        next_cursor = int(items[-1].created_at)

    stats = await get_rating_stats(settings_id, tag)

    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=30"
        response.headers["X-Page-Limit"] = str(limit)
        if next_cursor is not None:
            response.headers["X-Next-Cursor"] = str(next_cursor)

    return KeysetPage(
        items=items,
        next_cursor=next_cursor,
        review_count=stats.review_count,
        avg_rating=stats.avg_rating,
    )


@paidreviews_api_router.post("/api/v1/review", status_code=HTTPStatus.CREATED)
async def api_make_review(data: PostReview) -> dict:
    if not data.settings_id or data.settings_id == "":
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Settings ID is required."
        )
    settings = await get_settings_from_id(data.settings_id)
    if not settings or not settings.wallet:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Paid Reviews settings not set up properly.",
        )
    if data.tag not in settings.tags:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Tag not allowed."
        )
    if (
        data.comment
        and settings.comment_word_limit
        and len(data.comment) > settings.comment_word_limit
    ):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=(
                "Comment must be smaller than "
                f"{settings.comment_word_limit} characters."
            ),
        )
    try:
        review = Review(
            settings_id=settings.id,
            name=data.name,
            tag=data.tag,
            rating=data.rating,
            comment=data.comment,
            paid=False,
        )

        if not settings.cost or settings.cost == 0:
            review.paid = True
            review.payment_hash = "free"
        else:
            payment = await create_invoice(
                wallet_id=settings.wallet,
                amount=settings.cost or 0,
                memo=(f"Paid review for {data.tag}"),
                extra={
                    "tag": "paidreviews",
                    "amount": settings.cost,
                },
            )
            review.payment_hash = payment.payment_hash
            await create_review(review)
            return {
                "payment_hash": payment.payment_hash,
                "payment_request": payment.bolt11,
            }
        await create_review(review)
        return {"message": True}

    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Could not create invoice.",
        ) from e


@paidreviews_api_router.delete("/api/v1/review/{review_id}")
async def api_delete_review(
    review_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
) -> None:
    review = await get_review(review_id)
    logger.debug(review)
    if not review or not review.settings_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Review does not exist."
        )
    settings = await get_settings_from_id(review.settings_id)
    if not settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Settings do not exist."
        )
    if settings.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your extension."
        )

    await delete_review(review_id)
    return
