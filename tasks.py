import asyncio

from lnbits.core.models import Payment
from lnbits.core.services import get_pr_from_lnurl, pay_invoice
from lnbits.tasks import register_invoice_listener
from loguru import logger

from .crud import get_review_by_hash, get_settings_from_id, update_review


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_paidreviews")
    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") != "paidreviews":
        return
    review = await get_review_by_hash(payment.payment_hash)
    if not review:
        return
    logger.debug(review)
    try:
        if payment and payment.payment_hash:
            review.paid = True
            review.payment_hash = payment.payment_hash
            await update_review(review)
            settings = await get_settings_from_id(review.settings_id)
            if not settings:
                return
            await pay_tribute(settings.cost, settings.wallet)
    except Exception:
        return


async def pay_tribute(haircut_amount: int, wallet_id: str) -> None:
    try:
        tribute = int(2 * (haircut_amount / 100))
        try:
            pr = await get_pr_from_lnurl("lnbits@nostr.com", tribute * 1000)
        except Exception:
            return
        await pay_invoice(
            wallet_id=wallet_id,
            payment_request=pr,
            max_sat=tribute,
            description="Tribute to help support LNbits",
        )
    except Exception:
        pass
    return
