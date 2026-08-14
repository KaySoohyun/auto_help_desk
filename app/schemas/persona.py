from pydantic import BaseModel


class PersonaProfile(BaseModel):
    """Perfil del cliente (portal de personas)."""

    id: int
    name: str
    email: str | None
    company: str | None
    tenant_id: str
    tenant_name: str
