from contextvars import ContextVar

client_ip_var: ContextVar[str] = ContextVar("client_ip", default="unknown")
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
auth_context_var: ContextVar[dict[str, int | None] | None] = ContextVar(
    "auth_context", default=None
)
