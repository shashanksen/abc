"""
Custom error codes — single source of truth.

Format:  CDP-<DOMAIN>-<NUMBER>
   CDP    : platform prefix
   DOMAIN : 3-letter functionality code
   NUMBER : 4-digit zero-padded ID

Examples:
   CDP-AUT-0001  → invalid credentials
   CDP-USR-0010  → user not found
   CDP-DQR-0020  → DQ dimension code already exists

To add a new error:
  1. Pick a domain (or add a new one to ErrorDomain)
  2. Add the entry to ERROR_CATALOG
  3. Use AppError(code="CDP-XXX-NNNN") in your service
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorDomain(str, Enum):
    AUTH        = "AUT"
    USER        = "USR"
    MODULE      = "MOD"
    ACCESS      = "ACC"
    AUDIT       = "AUD"
    DQ_RULE     = "DQR"
    DQ_DIM      = "DQD"
    AGENT       = "AGT"
    SECURITY    = "SEC"
    INTERNAL    = "SYS"
    VALIDATION  = "VAL"


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    message: str
    http_status: int = 400


# ═══════════════════════════════════════════════════════════════════════════════
# Catalog — every known error registered here.
# ═══════════════════════════════════════════════════════════════════════════════
ERROR_CATALOG: dict[str, ErrorSpec] = {

    # ── Auth ──────────────────────────────────────────────────────────────────
    "CDP-AUT-0001": ErrorSpec("CDP-AUT-0001", "Invalid email or password",                401),
    "CDP-AUT-0002": ErrorSpec("CDP-AUT-0002", "Token expired",                            401),
    "CDP-AUT-0003": ErrorSpec("CDP-AUT-0003", "Token invalid or malformed",               401),
    "CDP-AUT-0004": ErrorSpec("CDP-AUT-0004", "User account disabled",                    403),
    "CDP-AUT-0005": ErrorSpec("CDP-AUT-0005", "Email already registered",                 409),
    "CDP-AUT-0006": ErrorSpec("CDP-AUT-0006", "Authentication required",                  401),
    "CDP-AUT-0007": ErrorSpec("CDP-AUT-0007", "Invalid agent callback token",             401),
    "CDP-AUT-0008": ErrorSpec("CDP-AUT-0008", "Agent callback token scope mismatch",      403),

    # ── User ──────────────────────────────────────────────────────────────────
    "CDP-USR-0010": ErrorSpec("CDP-USR-0010", "User not found",                           404),
    "CDP-USR-0011": ErrorSpec("CDP-USR-0011", "Cannot delete own account",                400),

    # ── Module ────────────────────────────────────────────────────────────────
    "CDP-MOD-0020": ErrorSpec("CDP-MOD-0020", "Module not found",                         404),
    "CDP-MOD-0021": ErrorSpec("CDP-MOD-0021", "Module disabled",                          403),
    "CDP-MOD-0022": ErrorSpec("CDP-MOD-0022", "Feature not found in module",              404),

    # ── Access (RBAC) ─────────────────────────────────────────────────────────
    "CDP-ACC-0030": ErrorSpec("CDP-ACC-0030", "Forbidden — insufficient role",            403),
    "CDP-ACC-0031": ErrorSpec("CDP-ACC-0031", "User has no access to this module",        403),
    "CDP-ACC-0032": ErrorSpec("CDP-ACC-0032", "Access request not found",                 404),
    "CDP-ACC-0033": ErrorSpec("CDP-ACC-0033", "Access request already decided",           409),
    "CDP-ACC-0034": ErrorSpec("CDP-ACC-0034", "Duplicate access request pending",         409),
    "CDP-ACC-0035": ErrorSpec("CDP-ACC-0035", "Admin privilege required",                 403),

    # ── DQ Dimensions ─────────────────────────────────────────────────────────
    "CDP-DQD-0040": ErrorSpec("CDP-DQD-0040", "DQ dimension not found",                   404),
    "CDP-DQD-0041": ErrorSpec("CDP-DQD-0041", "DQ dimension code already exists",         409),
    "CDP-DQD-0042": ErrorSpec("CDP-DQD-0042", "Cannot retire dimension with active rules",409),

    # ── DQ Rules ──────────────────────────────────────────────────────────────
    "CDP-DQR-0050": ErrorSpec("CDP-DQR-0050", "DQ rule not found",                        404),
    "CDP-DQR-0051": ErrorSpec("CDP-DQR-0051", "DQ rule code already exists",              409),
    "CDP-DQR-0052": ErrorSpec("CDP-DQR-0052", "Rule expression invalid",                  400),

    # ── Validation ────────────────────────────────────────────────────────────
    "CDP-VAL-0060": ErrorSpec("CDP-VAL-0060", "Request payload invalid",                  400),

    # ── Agent (LLM via A2A) ───────────────────────────────────────────────────
    "CDP-AGT-0070": ErrorSpec("CDP-AGT-0070", "Agent unavailable",                        503),
    "CDP-AGT-0071": ErrorSpec("CDP-AGT-0071", "Agent rejected credentials",               502),
    "CDP-AGT-0072": ErrorSpec("CDP-AGT-0072", "Agent returned invalid response",          502),
    "CDP-AGT-0073": ErrorSpec("CDP-AGT-0073", "Agent skill failed",                       422),
    "CDP-AGT-0074": ErrorSpec("CDP-AGT-0074", "Agent request timed out",                  504),
    "CDP-AGT-0075": ErrorSpec("CDP-AGT-0075", "Agent task not found",                     404),
    "CDP-AGT-0076": ErrorSpec("CDP-AGT-0076", "Agent input invalid",                      400),
    "CDP-AGT-0077": ErrorSpec("CDP-AGT-0077", "Daily AI usage budget exceeded",           429),
    "CDP-AGT-0078": ErrorSpec("CDP-AGT-0078", "Agent rate limit exceeded",                429),
    "CDP-AGT-0079": ErrorSpec("CDP-AGT-0079", "Agent graph state error",                  500),
    "CDP-AGT-0080": ErrorSpec("CDP-AGT-0080", "Agent functionality disabled by administrator", 503),

    # ── Security policy ───────────────────────────────────────────────────────
    "CDP-SEC-0100": ErrorSpec("CDP-SEC-0100", "Request rejected by content policy",       422),
    "CDP-SEC-0101": ErrorSpec("CDP-SEC-0101", "Generated output rejected",                422),
    "CDP-SEC-0102": ErrorSpec("CDP-SEC-0102", "Tool input rejected",                      422),

    # ── System ────────────────────────────────────────────────────────────────
    "CDP-SYS-0090": ErrorSpec("CDP-SYS-0090", "Database error",                           500),
    "CDP-SYS-0091": ErrorSpec("CDP-SYS-0091", "Unexpected internal error",                500),
    "CDP-SYS-0092": ErrorSpec("CDP-SYS-0092", "Service temporarily unavailable",          503),
}


class AppError(Exception):
    """Raised by services to signal a known error condition.

    The handler converts this to a JSON response with the right HTTP status
    and structured error payload.
    """
    def __init__(self, code: str, *, detail: str | None = None, context: dict[str, Any] | None = None):
        spec = ERROR_CATALOG.get(code)
        if spec is None:
            spec = ERROR_CATALOG["CDP-SYS-0091"]
            detail = f"Unregistered error code: {code}. Original detail: {detail or ''}"

        self.code = spec.code
        self.message = spec.message
        self.detail = detail
        self.context = context or {}
        self.http_status = spec.http_status
        super().__init__(f"[{self.code}] {self.message}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "detail": self.detail,
                "context": self.context,
            }
        }
