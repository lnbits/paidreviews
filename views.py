from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer
from lnbits.settings import settings

from .crud import get_rating_stats, get_reviews_by_tag, get_settings_from_id

paidreviews_generic_router = APIRouter()


def paidreviews_renderer():
    return template_renderer(["paidreviews/templates"])


# Backend


@paidreviews_generic_router.get("/", response_class=HTMLResponse)
async def index(req: Request, user: User = Depends(check_user_exists)):
    return paidreviews_renderer().TemplateResponse(
        "paidreviews/index.html", {"request": req, "user": user.json()}
    )


# Frontend


@paidreviews_generic_router.get("/{settings_id}/{tag}")
async def myextension(req: Request, settings_id: str, tag: str):
    pr_settings = await get_settings_from_id(settings_id)
    if not pr_settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Paid Reviews settings do not exist.",
        )
    if tag not in pr_settings.tags:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Tag does not exist."
        )

    # Initial page only; hardcode page size
    reviews = await get_reviews_by_tag(settings_id=settings_id, tag=tag)

    stats = await get_rating_stats(settings_id, tag)

    return paidreviews_renderer().TemplateResponse(
        "paidreviews/paidreviews.html",
        {
            "request": req,
            "pr_cost": pr_settings.cost,
            "pr_settings_id": settings_id,
            "pr_name": pr_settings.name,
            "pr_description": pr_settings.description,
            "pr_tag": tag,
            "pr_comment_word_limit": pr_settings.comment_word_limit,
            "pr_reviews": jsonable_encoder(reviews),
            "pr_review_count": stats.review_count,
            "pr_avg_rating": stats.avg_rating,
            "web_manifest": f"/paidreviews/manifest/{settings_id}/{tag}.webmanifest",
        },
    )


# Manifest for public page


@paidreviews_generic_router.get("/manifest/{settings_id}/{tag}.webmanifest")
async def manifest(settings_id: str, tag: str):
    pr_settings = await get_settings_from_id(settings_id)
    if not pr_settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Paid Reviews settings do not exist.",
        )
    if tag not in pr_settings.tags:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Tag does not exist."
        )

    name = f"{pr_settings.name} - {settings.lnbits_site_title}"
    url = "/paidreviews/" + settings_id + "/" + tag
    return {
        "short_name": settings.lnbits_site_title,
        "name": name,
        "icons": [
            {
                "src": (
                    settings.lnbits_custom_logo
                    if settings.lnbits_custom_logo
                    else "https://cdn.jsdelivr.net/gh/lnbits/lnbits@0.3.0/docs/logos/lnbits.png"
                ),
                "type": "image/png",
                "sizes": "900x900",
            }
        ],
        "start_url": url,
        "background_color": "#1F2234",
        "description": "Minimal extension to build on",
        "display": "standalone",
        "scope": url,
        "theme_color": "#1F2234",
        "shortcuts": [
            {
                "name": name,
                "short_name": pr_settings.name,
                "description": name,
                "url": url,
            }
        ],
    }
