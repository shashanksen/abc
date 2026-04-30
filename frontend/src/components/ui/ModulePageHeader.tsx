import { type ReactNode } from 'react';

interface ModulePageHeaderProps {
  title: string;
  subtitle: string;
  aside?: ReactNode;
}

export function ModulePageHeader({ title, subtitle, aside }: ModulePageHeaderProps) {
  return (
    <header className="page-header module-page-header">
      <div>
        <h1 className="page-title">{title}</h1>
        <p className="page-subtitle">{subtitle}</p>
      </div>
      {aside ? <div className="module-page-header-aside">{aside}</div> : null}
    </header>
  );
}