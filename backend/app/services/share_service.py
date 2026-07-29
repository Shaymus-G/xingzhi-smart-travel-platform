"""旅行计划分享 Service"""
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.plan_share import PlanShare, _generate_share_token, hash_token
from app.models.travel_plan import TravelPlan

DEFAULT_EXPIRE_HOURS = 72


def create_share(
    db: Session, plan_id: int, user_id: int,
    expires_in_hours: int = DEFAULT_EXPIRE_HOURS,
    include_budget: bool = False,
) -> dict:
    """为计划创建公开分享"""
    plan = db.scalar(
        select(TravelPlan).where(TravelPlan.id == plan_id, TravelPlan.user_id == user_id)
    )
    if not plan:
        return {"error": "计划不存在"}

    # 构建快照（只含公开字段）
    snapshot = _build_snapshot(plan, include_budget)
    raw_token = _generate_share_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

    share = PlanShare(
        plan_id=plan.id,
        token_hash=hash_token(raw_token),
        snapshot_json=json.dumps(snapshot, ensure_ascii=False),
        include_budget=include_budget,
        expires_at=expires_at,
    )
    db.add(share)
    db.commit()
    db.refresh(share)

    return {
        "share_id": share.id,
        "share_token": raw_token,
        "share_url": f"/api/public/plan-shares/{raw_token}",
        "expires_at": share.expires_at.isoformat(),
        "created_at": share.created_at.isoformat() if share.created_at else None,
    }


def get_shares_by_plan(db: Session, plan_id: int, user_id: int) -> list[dict]:
    """获取计划的分享列表（仅所有者）"""
    plan = db.scalar(
        select(TravelPlan).where(TravelPlan.id == plan_id, TravelPlan.user_id == user_id)
    )
    if not plan:
        return []

    shares = db.scalars(
        select(PlanShare).where(PlanShare.plan_id == plan_id).order_by(PlanShare.created_at.desc())
    ).all()
    return [_share_to_dict(s) for s in shares]


def get_public_share(db: Session, token: str) -> Optional[dict]:
    """公开查询分享快照（无需登录）"""
    token_h = hash_token(token)
    share = db.scalar(
        select(PlanShare).where(
            PlanShare.token_hash == token_h,
            PlanShare.status == "active",
            PlanShare.expires_at > datetime.now(timezone.utc),
        )
    )
    if not share:
        return None
    try:
        snapshot = json.loads(share.snapshot_json)
    except json.JSONDecodeError:
        return None
    snapshot["created_at"] = share.created_at.isoformat() if share.created_at else None
    snapshot["expires_at"] = share.expires_at.isoformat()
    return snapshot


def revoke_share(db: Session, plan_id: int, share_id: int, user_id: int) -> bool:
    """撤销分享（仅计划所有者）"""
    plan = db.scalar(
        select(TravelPlan).where(TravelPlan.id == plan_id, TravelPlan.user_id == user_id)
    )
    if not plan:
        return False
    share = db.scalar(
        select(PlanShare).where(PlanShare.id == share_id, PlanShare.plan_id == plan_id)
    )
    if not share:
        return False
    share.status = "revoked"
    db.commit()
    return True


def _build_snapshot(plan: TravelPlan, include_budget: bool) -> dict:
    """从计划构建公开快照（仅包含公开字段，脱敏处理）"""
    snapshot = {
        "title": plan.title,
        "destination": plan.destination,
        "days": plan.days,
        "budget": plan.budget if include_budget else None,
        "plan_json": _filter_public_fields(plan.plan_json) if plan.plan_json else None,
    }
    if plan.plan_json:
        snapshot["itinerary"] = _extract_itinerary(plan.plan_json)
    return snapshot


def _filter_public_fields(plan_json: dict) -> dict:
    """过滤 plan_json 中的敏感字段"""
    if not isinstance(plan_json, dict):
        return {}
    allowed = {"schema_version", "title", "destination", "days", "travelers", "summary", "budget", "itinerary", "tips", "assumptions"}
    return {k: v for k, v in plan_json.items() if k in allowed}


def _extract_itinerary(plan_json: dict) -> list:
    """提取 itinerary 中的公开字段（去掉 resource_id / city_id / 内部坐标等）"""
    itinerary = plan_json.get("itinerary", [])
    if not isinstance(itinerary, list):
        return []
    result = []
    for day in itinerary:
        day_items = []
        for item in day.get("items", []):
            day_items.append({
                "name": item.get("name", ""),
                "period": item.get("period", ""),
                "start_time": item.get("start_time"),
                "end_time": item.get("end_time"),
                "resource_type": item.get("resource_type"),
                "address": item.get("address"),
                "estimated_cost": item.get("estimated_cost", 0),
            })
        result.append({"day": day.get("day"), "theme": day.get("theme", ""), "items": day_items})
    return result


def _share_to_dict(s: PlanShare) -> dict:
    return {
        "share_id": s.id,
        "share_url": f"/api/public/plan-shares/{s.token_hash[:16]}",
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "expires_at": s.expires_at.isoformat(),
        "status": s.status,
        "include_budget": s.include_budget,
    }
