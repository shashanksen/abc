# Adding a new module

End-to-end recipe to plug a new module into the platform. Example:
**Lineage**.

## 1. Database — register the module

```sql
-- modules row
INSERT INTO core.modules (code, name, description, icon, sort_order) VALUES
  ('LINEAGE', 'Data Lineage', 'Track data flow', 'git-branch', 20)
ON CONFLICT (code) DO NOTHING;

-- roles
INSERT INTO core.module_roles (module_id, code, name, description, permissions)
SELECT id, 'ADMIN',  'Module Admin',  'Full control',          '["read","write","delete","manage"]'::jsonb FROM core.modules WHERE code='LINEAGE'
UNION ALL
SELECT id, 'EDITOR', 'Module Editor', 'Create + update',       '["read","write"]'::jsonb               FROM core.modules WHERE code='LINEAGE'
UNION ALL
SELECT id, 'VIEWER', 'Module Viewer', 'Read-only',             '["read"]'::jsonb                       FROM core.modules WHERE code='LINEAGE'
ON CONFLICT DO NOTHING;

-- features (tabs)
INSERT INTO core.module_features (module_id, code, name, sort_order)
SELECT m.id, 'DASHBOARD', 'My Dashboard', 10 FROM core.modules m WHERE m.code='LINEAGE'
UNION ALL
SELECT m.id, 'GRAPH',     'Graph View',   20 FROM core.modules m WHERE m.code='LINEAGE'
ON CONFLICT DO NOTHING;
```

If your module has its own data tables, create them in their own schema
(`CREATE SCHEMA lineage;` then your tables there) — keeps modules isolated.

## 2. Backend — module package

```
backend/app/modules/lineage/
├── __init__.py
├── models.py     # ORM models (your_schema.your_tables)
└── router.py     # FastAPI router with require_module_permission(...)
```

### `router.py` template

```python
MODULE_CODE = "LINEAGE"

router = APIRouter(prefix="/api/lineage", tags=["lineage"])
read_required  = require_module_permission(MODULE_CODE, permission="read")
write_required = require_module_permission(MODULE_CODE, permission="write")

@router.get("/something", response_model=list[SomeOut])
def list_something(
    db: Annotated[Session, Depends(db_session)],
    _user: Annotated[User, Depends(read_required)],
):
    return SomeService(db).list()
```

### Wire it into `app/main.py`

```python
from app.modules.lineage.router import router as lineage_router
app.include_router(lineage_router)
```

## 3. Add domain-specific error codes

Edit `backend/app/core/errors.py`:

```python
"CDP-LIN-0070": ErrorSpec("CDP-LIN-0070", "Lineage edge not found", 404),
"CDP-LIN-0071": ErrorSpec("CDP-LIN-0071", "Cycle detected in lineage graph", 409),
```

## 4. Frontend — register module + API client

### Register in `frontend/src/lib/moduleRegistry.ts`:

```ts
moduleRegistry.register({
  code: 'LINEAGE',
  name: 'Data Lineage',
  basePath: '/lineage',
  features: [
    { code: 'DASHBOARD', name: 'My Dashboard', path: '/',      defaultPermission: 'read' },
    { code: 'GRAPH',     name: 'Graph View',   path: '/graph', defaultPermission: 'read' },
  ],
});
```

### API client at `frontend/src/modules/lineage/api.ts`:

```ts
import { BaseApiClient } from '@/lib/apiClient';

class LineageApi extends BaseApiClient {
  list() { return this.get<unknown[]>('/lineage/something'); }
}

export const lineageApi = new LineageApi();
```

### Pages under `frontend/src/app/lineage/`:

```
src/app/lineage/
├── layout.tsx       # tab bar (copy DQ's, change `code: 'LINEAGE'`)
├── page.tsx         # dashboard
└── graph/page.tsx
```

## 5. Verify

1. Restart backend + frontend
2. Sign in as admin
3. Open Admin → Users — grant yourself `LINEAGE` access (any role)
4. Sidebar now shows the new module
5. Tabs render based on the registry
6. Backend enforces RBAC on every endpoint via `require_module_permission`

## Checklist

- [ ] DB rows: module, roles, features
- [ ] Optional schema for your module's tables
- [ ] `backend/app/modules/<code>/models.py`
- [ ] `backend/app/modules/<code>/router.py`
- [ ] Errors registered in `core/errors.py`
- [ ] Router included in `app/main.py`
- [ ] `moduleRegistry.register({...})` in frontend
- [ ] `frontend/src/modules/<code>/api.ts`
- [ ] Pages in `frontend/src/app/<basePath>/...`
- [ ] User-friendly error messages added to `frontend/src/lib/errors.ts`
