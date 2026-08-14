from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_effective_tenant_ids
from app.core.permissions import READ_TICKETS, require_permissions
from app.database import get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import CustomerOut

router = APIRouter(prefix="/v1/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
def list_customers(
    current_user: User = Depends(require_permissions(READ_TICKETS)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[CustomerOut]:
    """Lista los customers del/los tenant(s) del usuario."""
    customers = (
        db.query(Customer)
        .filter(Customer.tenant_id.in_(tenant_ids))
        .order_by(Customer.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    return [CustomerOut.model_validate(customer) for customer in customers]


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    current_user: User = Depends(require_permissions(READ_TICKETS)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
) -> CustomerOut:
    """Obtiene un customer por ID."""
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.tenant_id.in_(tenant_ids))
        .first()
    )
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer no encontrado",
        )
    
    return CustomerOut.model_validate(customer)
