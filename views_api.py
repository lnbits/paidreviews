from http import HTTPStatus

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from lnbits.core.models.users import AccountId
from lnbits.core.services import create_invoice
from lnbits.db import Filters
from lnbits.decorators import check_account_id_exists, parse_filters

from .crud import (
    RatingsFilters,
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
    PostReview,
    PRSettings,
    RatingStats,
    Review,
    ReviewstPage,
)

paidreviews_api_router = APIRouter()

############################# Settings #############################


@paidreviews_api_router.get("/api/v1/settings")
async def api_settings(
    account_id: AccountId = Depends(check_account_id_exists),
) -> PRSettings:
    pr_settings = await get_settings(account_id.id)
    if not pr_settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Update the settings."
        )
    return pr_settings


@paidreviews_api_router.post("/api/v1/settings")
async def api_create_settings(
    data: CreatePrSettings,
    account_id: AccountId = Depends(check_account_id_exists),
) -> PRSettings:
    settings = PRSettings(**data.dict())
    settings.user_id = account_id.id
    settings = await create_settings(settings)
    return settings


@paidreviews_api_router.put("/api/v1/settings/{settings_id}")
async def api_update_settings(
    settings_id: str,
    data: CreatePrSettings,
    account_id: AccountId = Depends(check_account_id_exists),
) -> PRSettings:
    settings = await get_settings_from_id(settings_id)
    if not settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Settings do not exist."
        )

    if settings.user_id != account_id.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your reviews."
        )

    for field, value in data.dict().items():
        if value is not None:
            setattr(settings, field, value)

    settings = await update_settings(settings)
    return settings


############################## Tags #############################


@paidreviews_api_router.get("/api/v1/{settings_id}/tags")
async def api_get_tags(response: Response, settings_id: str) -> list[RatingStats]:
    tags = await get_rating_stats_for_all_tags(settings_id)
    if not tags:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="No tags found.")
    response.headers["Cache-Control"] = "public, max-age=30"
    return tags


@paidreviews_api_router.post("/api/v1/{settings_id}/tags/sync")
async def api_sync_tags_from_manifest(
    response: Response,
    settings_id: str,
    account_id: AccountId = Depends(check_account_id_exists),
) -> dict:
    settings = await get_settings_from_id(settings_id)
    if not settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Settings do not exist."
        )
    if settings.user_id != account_id.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your reviews."
        )
    manifest_url = "https://raw.githubusercontent.com/lnbits/lnbits-extensions/refs/heads/main/extensions.json"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(manifest_url)
            r.raise_for_status()
            manifest = r.json()
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY, detail="Could not load manifest."
        ) from e

    ids = set()
    for ext in manifest.get("extensions", []) or []:
        if isinstance(ext, dict) and ext.get("id"):
            ids.add(ext["id"].strip())
    if not ids:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="No extension ids found.",
        )

    current = set(settings.tags or [])
    added = sorted(ids - current)

    if added:
        settings.tags = sorted(current | ids)
        await update_settings(settings)

    response.headers["Cache-Control"] = "no-store"
    return {
        "added_count": len(added),
        "added": added,
        "total_tags": len(settings.tags or []),
    }


############################# Reviews #############################

## TO DO:
## Delete unpaid reviiews after a certain time period


@paidreviews_api_router.get("/api/v1/{settings_id}/reviews/{tag}")
async def api_reviews_by_tag(
    settings_id: str,
    tag: str,
    filters: Filters = Depends(parse_filters(RatingsFilters)),
) -> ReviewstPage:
    reviews = await get_reviews_by_tag(
        settings_id=settings_id,
        tag=tag,
        filters=filters,
    )

    stats = await get_rating_stats(settings_id, tag)

    return ReviewstPage(
        data=reviews.data,  # type: ignore
        total=reviews.total,
        avg_rating=stats.avg_rating,
    )


@paidreviews_api_router.post(
    "/api/v1/{settings_id}/reviews", status_code=HTTPStatus.CREATED
)
async def api_make_review(settings_id: str, data: PostReview) -> dict:
    if not settings_id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Settings ID is required."
        )

    settings = await get_settings_from_id(settings_id)
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


@paidreviews_api_router.delete("/api/v1/{settings_id}/reviews/{review_id}")
async def api_delete_review(
    settings_id: str,
    review_id: str,
    account_id: AccountId = Depends(check_account_id_exists),
) -> None:
    settings = await get_settings(account_id.id)
    if not settings or settings.id != settings_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Settings do not exist."
        )
    review = await get_review(review_id)
    if not review or not review.settings_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Review does not exist."
        )

    if settings.id != review.settings_id:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Bad review id.")
    if settings.user_id != account_id.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your extension."
        )

    await delete_review(review_id)
    return
