import asyncio

from fastapi import APIRouter
from lnbits.tasks import create_permanent_unique_task
from loguru import logger

from .crud import db
from .tasks import wait_for_paid_invoices
from .views import paidreviews_generic_router
from .views_api import paidreviews_api_router

paidreviews_ext: APIRouter = APIRouter(prefix="/paidreviews", tags=["PaidReviews"])
paidreviews_ext.include_router(paidreviews_generic_router)
paidreviews_ext.include_router(paidreviews_api_router)

paidreviews_static_files = [
    {
        "path": "/paidreviews/static",
        "name": "paidreviews_static",
    }
]

scheduled_tasks: list[asyncio.Task] = []


def paidreviews_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def paidreviews_start():
    task = create_permanent_unique_task("ext_paidreviews", wait_for_paid_invoices)
    scheduled_tasks.append(task)


__all__ = [
    "db",
    "paidreviews_ext",
    "paidreviews_start",
    "paidreviews_static_files",
    "paidreviews_stop",
]
