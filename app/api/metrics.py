from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.db.session import get_session

router = APIRouter(tags=["metrics"])


@router.get("/metrics/basic")
async def metrics_basic():
    db = get_session()
    if not db:
        raise HTTPException(status_code=500, detail="DB not configured")

    # NOTE: assumes your query log table is named "queries"
    # and provider calls table is named "provider_calls"
    # If yours differ (e.g. query_logs), tell me and I’ll adjust.

    total_queries = db.execute(text("select count(*) from queries")).scalar() or 0

    queries_last_24h = db.execute(
        text("select count(*) from queries where received_at >= now() - interval '24 hours'")
    ).scalar() or 0

    unique_sessions_last_24h = db.execute(
        text(
            "select count(distinct session_id) from queries "
            "where session_id is not null and received_at >= now() - interval '24 hours'"
        )
    ).scalar() or 0

    new_users_last_7d = db.execute(
        text("select count(*) from users where created_at >= now() - interval '7 days'")
    ).scalar() or 0

    anonymous_sessions_last_24h = db.execute(
        text(
            "select count(*) from chat_sessions "
            "where is_anonymous = true and created_at >= now() - interval '24 hours'"
        )
    ).scalar() or 0

    claimed_sessions_last_24h = db.execute(
        text(
            "select count(*) from chat_sessions "
            "where is_anonymous = false and last_seen_at >= now() - interval '24 hours'"
        )
    ).scalar() or 0

    avg_latency_ms_last_24h = db.execute(
        text(
            "select coalesce(avg(latency_total_ms), 0) "
            "from queries where received_at >= now() - interval '24 hours'"
        )
    ).scalar() or 0

    provider_success_rate_last_24h = db.execute(
        text(
            "select case when count(*) = 0 then 0 "
            "else round(100.0 * sum(case when success then 1 else 0 end) / count(*), 2) end "
            "from provider_calls where started_at >= now() - interval '24 hours'"
        )
    ).scalar() or 0

    multi_call_rate_last_24h = db.execute(
        text(
            "select case when count(*) = 0 then 0 "
            "else round(100.0 * sum(case when multi_call then 1 else 0 end) / count(*), 2) end "
            "from queries where received_at >= now() - interval '24 hours'"
        )
    ).scalar() or 0

    top_intents_last_24h = db.execute(
        text(
            "select router_intent, count(*) as n "
            "from queries "
            "where received_at >= now() - interval '24 hours' "
            "group by router_intent "
            "order by n desc "
            "limit 8"
        )
    ).fetchall()

    db.close()

    return {
        "ok": True,
        "usage": {
            "total_queries": int(total_queries),
            "queries_last_24h": int(queries_last_24h),
            "unique_sessions_last_24h": int(unique_sessions_last_24h),
            "new_users_last_7d": int(new_users_last_7d),
            "anonymous_sessions_last_24h": int(anonymous_sessions_last_24h),
            "claimed_sessions_last_24h": int(claimed_sessions_last_24h),
        },
        "performance": {
            "avg_latency_ms_last_24h": float(avg_latency_ms_last_24h),
            "provider_success_rate_last_24h": float(provider_success_rate_last_24h),
            "multi_call_rate_last_24h": float(multi_call_rate_last_24h),
        },
        "top_intents_last_24h": [{"intent": r[0], "count": int(r[1])} for r in top_intents_last_24h],
    }
