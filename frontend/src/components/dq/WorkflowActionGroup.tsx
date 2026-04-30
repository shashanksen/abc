interface WorkflowActionGroupProps {
  actions: string[];
}

function actionClassName(action: string) {
  if (action === 'Implement' || action === 'Approve') return 'btn btn-primary btn-sm';
  if (action === 'Upload') return 'btn btn-primary';
  return 'btn btn-secondary btn-sm';
}

export function WorkflowActionGroup({ actions }: WorkflowActionGroupProps) {
  return (
    <div className="action-strip">
      {actions.map((action) => (
        <button key={action} type="button" className={actionClassName(action)}>
          {action}
        </button>
      ))}
    </div>
  );
}