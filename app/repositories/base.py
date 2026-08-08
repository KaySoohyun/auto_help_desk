from typing import Any, Generic, Iterable, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class TenantScopedRepository(Generic[ModelT]):
    """Repositorio que aplica filtro obligatorio por tenant (ADR-001).

    Toda consulta a tablas de negocio debe pasar por este repositorio para
    garantizar el aislamiento. El tenant_id proviene del JWT, nunca del cliente.
    """

    tenant_id_attr = "tenant_id"

    def __init__(self, db: Session, model: type[ModelT], tenant_id: str) -> None:
        self.db = db
        self.model = model
        self.tenant_id = tenant_id

    def _assert_tenant(self, obj: ModelT) -> None:
        if getattr(obj, self.tenant_id_attr) != self.tenant_id:
            raise PermissionError("Recurso de otro tenant")

    def get_or_none(self, pk) -> ModelT | None:
        obj = self.db.get(self.model, pk)
        if obj is None:
            return None
        self._assert_tenant(obj)
        return obj

    def list(self) -> Iterable[ModelT]:
        stmt = select(self.model).where(
            getattr(self.model, self.tenant_id_attr) == self.tenant_id
        )
        return self.db.scalars(stmt).all()

    def add(self, obj: ModelT) -> ModelT:
        setattr(obj, self.tenant_id_attr, self.tenant_id)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj