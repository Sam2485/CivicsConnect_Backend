from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Issue, IssueCategory, IssueStatus, User
from app.schemas import DashboardResponse

router = APIRouter(tags=["dashboard"])


def display_issue_id(issue: Issue) -> str:
    return f"C{1000 + (int(issue.id.hex[-6:], 16) % 9000)}"


def category_label(category: IssueCategory) -> str:
    return category.value.replace("_", " ").title()


def status_label(status: IssueStatus) -> str:
    return status.value.replace("_", " ").title()


def relative_time(value: datetime) -> str:
    now = datetime.now(value.tzinfo)
    delta = now - value
    if delta < timedelta(minutes=1):
        return "Just now"
    if delta < timedelta(hours=1):
        return f"{int(delta.total_seconds() // 60)} min ago"
    if delta < timedelta(days=1):
        return f"{int(delta.total_seconds() // 3600)} hr ago"
    return value.strftime("%d %b, %H:%M")


def score(part: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((part / total) * 100)


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardResponse:
    query = select(Issue)
    if user.role.value == "citizen":
        query = query.where(Issue.reporter_id == user.id)

    issues = list(db.scalars(query.order_by(Issue.created_at.desc())).all())
    total = len(issues)
    resolved = len([issue for issue in issues if issue.status == IssueStatus.resolved])
    pending = len([issue for issue in issues if issue.status != IssueStatus.resolved])
    nearby = len([issue for issue in issues if issue.status == IssueStatus.pending])
    verified = len([issue for issue in issues if issue.verified_count > 0])
    community_score = round((score(resolved, total) * 0.55) + (score(verified, total) * 0.25) + 20) if total else 0

    category_counts = {
        category: len([issue for issue in issues if issue.category == category])
        for category in IssueCategory
    }
    top_category = max(category_counts, key=category_counts.get) if total else None
    infrastructure_count = sum(category_counts[category] for category in [IssueCategory.pothole, IssueCategory.streetlight, IssueCategory.drainage])
    cleanliness_count = category_counts[IssueCategory.garbage]

    today = date.today()
    line_chart = []
    for days_back in range(6, -1, -1):
        day = today - timedelta(days=days_back)
        line_chart.append(
            {
                "label": day.strftime("%a"),
                "issues": len([issue for issue in issues if issue.created_at.date() == day]),
            }
        )

    recent = [
        {
            "id": display_issue_id(issue),
            "title": issue.title,
            "category": category_label(issue.category),
            "status": status_label(issue.status),
            "location": f"{issue.latitude:.4f}, {issue.longitude:.4f}",
            "reported_at": relative_time(issue.created_at),
        }
        for issue in issues[:5]
    ]

    ai_insights = []
    if total:
        ai_insights.append(
            {
                "title": f"{category_label(top_category)} is the largest share" if top_category else "Issue mix is still forming",
                "summary": f"{category_counts[top_category]} of {total} reports are in this category." if top_category else "Submit more reports to build better trends.",
                "confidence": min(95, 55 + score(category_counts[top_category], total)) if top_category else 50,
            }
        )
        ai_insights.append(
            {
                "title": "Resolution coverage",
                "summary": f"{resolved} of {total} reports are closed. {pending} still need authority action.",
                "confidence": min(95, max(45, community_score)),
            }
        )
    else:
        ai_insights.append(
            {
                "title": "No reports submitted yet",
                "summary": "Submit your first civic report to build personal dashboard insights.",
                "confidence": 0,
            }
        )

    return DashboardResponse(
        total_issues=total,
        resolved_issues=resolved,
        pending_issues=pending,
        nearby_issues=nearby,
        community_score=community_score,
        recent_issues=recent,
        ai_insights=ai_insights,
        community_health={
            "infrastructure": score(resolved, infrastructure_count) if infrastructure_count else 0,
            "cleanliness": score(len([issue for issue in issues if issue.category == IssueCategory.garbage and issue.status == IssueStatus.resolved]), cleanliness_count) if cleanliness_count else 0,
            "response": score(resolved, total),
        },
        line_chart=line_chart,
        pie_chart=[
            {"label": "Resolved", "value": resolved, "color": "#14b8a6"},
            {"label": "Pending", "value": pending, "color": "#f59e0b"},
            {"label": "Reported", "value": total, "color": "#2563eb"},
        ],
    )
