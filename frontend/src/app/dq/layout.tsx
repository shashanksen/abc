'use client';

import { type ReactNode } from 'react';
import { RouteGuard } from '@/components/RouteGuard';
import { AppShell } from '@/components/AppShell';
import { ModulePageHeader } from '@/components/ui/ModulePageHeader';
import { ModuleTabNav } from '@/components/ui/ModuleTabNav';

export default function DqLayout({ children }: { children: ReactNode }) {
  return (
    <RouteGuard>
      <AppShell>
        <DqInner>{children}</DqInner>
      </AppShell>
    </RouteGuard>
  );
}

function DqInner({ children }: { children: ReactNode }) {
  return (
    <>
      <ModulePageHeader
        title="Data Quality"
        subtitle="One stop for your Data Quality"
        aside={<span className="chip chip-primary">Workflow pilot</span>}
      />

      <ModuleTabNav moduleCode="DQ" />

      {children}
    </>
  );
}
