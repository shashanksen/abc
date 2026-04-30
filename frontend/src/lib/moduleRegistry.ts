/**
 * Module Registry
 *
 * To add a new module:
 *   1. Add a row to core.modules in the DB (with code & name)
 *   2. Create src/modules/<code>/<routes & components>
 *   3. Register here so the dashboard knows how to render it
 *
 * The backend remains generic — only this client-side registry needs updating
 * with the page component for new modules.
 */
import type { ComponentType } from 'react';

export interface ModuleConfig {
  /** must match core.modules.code in DB */
  code: string;
  /** label for nav */
  name: string;
  /** route prefix */
  basePath: string;
  /** which features map to which routes within the module */
  features: ModuleFeatureConfig[];
}

export interface ModuleFeatureConfig {
  /** must match core.module_features.code */
  code: string;
  name: string;
  path: string;        // sub-path under module basePath
  defaultPermission: 'read' | 'write';
}

class ModuleRegistry {
  private modules = new Map<string, ModuleConfig>();

  register(cfg: ModuleConfig): void {
    this.modules.set(cfg.code, cfg);
  }

  all(): ModuleConfig[] {
    return Array.from(this.modules.values());
  }

  get(code: string): ModuleConfig | undefined {
    return this.modules.get(code);
  }
}

export const moduleRegistry = new ModuleRegistry();

// ─── Register modules here ────────────────────────────────────────────────────
moduleRegistry.register({
  code: 'DQ',
  name: 'Data Quality',
  basePath: '/dq',
  features: [
    { code: 'DASHBOARD',       name: 'My Dashboard',     path: '/',                 defaultPermission: 'read' },
    { code: 'DIMENSIONS',      name: 'DQ Dimensions',    path: '/dimensions',       defaultPermission: 'read' },
    { code: 'EDE_MAPPINGS',    name: 'EDE Mappings',     path: '/ede-mappings',     defaultPermission: 'read' },
    { code: 'BUSINESS_RULES',  name: 'Business Rules',   path: '/business-rules',   defaultPermission: 'read' },
    { code: 'TECHNICAL_RULES', name: 'Technical Rules',  path: '/technical-rules',  defaultPermission: 'read' },
    { code: 'DQ_DASHBOARD',    name: 'DQ Dashboard',     path: '/dq-dashboard',     defaultPermission: 'read' },
  ],
});
