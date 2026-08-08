from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.core.metrics import metrics
from app.core.permissions import VIEW_AUDIT, require_permissions
from app.models.user import User

router = APIRouter(prefix="/v1/metrics", tags=["observabilidad"])


@router.get("", response_class=PlainTextResponse)
def get_metrics(
    current_user: User = Depends(require_permissions(VIEW_AUDIT)),
) -> str:
    """Expone las métricas en formato de texto Prometheus (§14.4)."""
    return metrics.render_prometheus()