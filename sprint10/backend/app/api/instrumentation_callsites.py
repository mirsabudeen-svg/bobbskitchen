"""
backend/app/api/instrumentation_callsites.py

Sprint 10 — Exactly where to add analytics track() calls in existing files.
This file is a reference guide, not executable code.
Each section shows the file, the existing code to find, and what to add.
"""

# ═════════════════════════════════════════════════════════════════════════════
# FILE: backend/app/api/sessions.py (or wherever sessions are created/abandoned)
# ═════════════════════════════════════════════════════════════════════════════

# FIND: the end of create_session(), after db.commit()
# ADD:
"""
    import asyncio
    from app.services.analytics import track_session_started
    asyncio.create_task(track_session_started(db, str(session.id)))
"""

# FIND: the end of abandon_session(), after db.commit()
# ADD:
"""
    asyncio.create_task(track_session_abandoned(db, str(session_id)))
"""


# ═════════════════════════════════════════════════════════════════════════════
# FILE: backend/app/api/ws.py (or wherever story is submitted and designs generated)
# ═════════════════════════════════════════════════════════════════════════════

# FIND: after story_text is received and validated, before fal.ai call
# ADD (record story submission):
"""
    import time
    from app.services.analytics import track_story_submitted
    story_digest = story_text[:100] if story_text else ""
    word_count = len((story_text or "").split())
    asyncio.create_task(
        track_story_submitted(db, str(session_id), word_count, story_digest)
    )
    _design_start_ms = int(time.monotonic() * 1000)
"""

# FIND: after fal.ai generation completes, when variants are ready
# ADD (record generation result):
"""
    from app.services.analytics import track_designs_generated, track_variant_generated
    latency_ms = int(time.monotonic() * 1000) - _design_start_ms
    asyncio.create_task(
        track_designs_generated(
            db,
            str(session_id),
            succeeded=len([v for v in variants if v.image_url]),
            failed=len([v for v in variants if not v.image_url]),
            latency_ms=latency_ms,
            styles=[v.style for v in variants if v.style],
            fal_model="fal-ai/flux",  # replace with actual model name
        )
    )
    for i, variant in enumerate(variants):
        asyncio.create_task(
            track_variant_generated(
                db,
                str(session_id),
                str(variant.id),
                style=variant.style or "unknown",
                prompt_digest=(variant.prompt or "")[:100],
                success=bool(variant.image_url),
                latency_ms=latency_ms // max(len(variants), 1),
            )
        )
"""

# FIND: after variant is selected (POST /designs/{id}/select or equivalent)
# ADD:
"""
    from app.services.analytics import track_variant_selected
    asyncio.create_task(
        track_variant_selected(
            db,
            str(session_id),
            str(variant.id),
            style=variant.style or "unknown",
            position=variant_position,  # index 0–3 in the generated set
        )
    )
"""


# ═════════════════════════════════════════════════════════════════════════════
# FILE: backend/app/api/orders.py — create_order()
# ═════════════════════════════════════════════════════════════════════════════

# FIND: after await db.commit() at the end of create_order()
# ADD:
"""
    import time
    from app.services.analytics import track_order_placed
    # story_started_at should be stored on the session model (add a column if not present)
    story_to_order_ms = int(
        (datetime.utcnow() - session.story_started_at).total_seconds() * 1000
    ) if hasattr(session, "story_started_at") and session.story_started_at else 0

    for item in order.items:
        asyncio.create_task(
            track_order_placed(
                db,
                str(order.session_id),
                str(order.id),
                order.short_ref,
                item.product_id,
                item.size,
                item.color,
                item.quantity,
                order.total_paise,
                story_to_order_ms,
            )
        )
"""


# ═════════════════════════════════════════════════════════════════════════════
# FILE: backend/app/api/orders.py — update_order_status()
# ═════════════════════════════════════════════════════════════════════════════

# FIND: after status is committed, inside update_order_status()
# ADD this block (handles paid, ready, collected, reprint):
"""
    from app.services.analytics import (
        track_order_paid, track_order_ready,
        track_order_collected, track_reprint,
    )

    if body.status == "ready":
        asyncio.create_task(
            track_order_ready(db, str(order.id), order.short_ref, order.created_at)
        )

    elif body.status == "collected":
        asyncio.create_task(
            track_order_collected(db, str(order.id), order.short_ref)
        )

    elif body.status in ("failed", "reprinting") and body.status == "reprinting":
        # Track reprint on the reprinting transition (not the failed one)
        for item in order.items:
            asyncio.create_task(
                track_reprint(
                    db,
                    str(order.id),
                    order.short_ref,
                    color=item.color,
                    product_id=item.product_id,
                    staff_notes=body.staff_notes,
                )
            )
"""


# ═════════════════════════════════════════════════════════════════════════════
# FILE: backend/app/api/orders.py — record_payment()
# ═════════════════════════════════════════════════════════════════════════════

# FIND: after payment is committed in record_payment()
# ADD:
"""
    from app.services.analytics import track_order_paid
    asyncio.create_task(
        track_order_paid(
            db,
            str(order.id),
            order.short_ref,
            body.payment_method,
            order.amount_paid_paise or order.total_paise,
        )
    )
"""


# ═════════════════════════════════════════════════════════════════════════════
# FILE: backend/app/services/whatsapp.py — send_artwork() result handling
# (in the orders.py update_order_status_with_whatsapp block from Sprint 9)
# ═════════════════════════════════════════════════════════════════════════════

# FIND: after log_entry is committed following send_artwork() call
# ADD:
"""
    from app.services.analytics import track_whatsapp_result
    asyncio.create_task(
        track_whatsapp_result(
            db,
            str(order.id),
            order.short_ref,
            success=result.success,
            language=result.language,
            error=result.error,
        )
    )
"""
