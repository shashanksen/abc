export type DqPersona = 'Central CDO' | 'BU CDO' | 'DQ Analyst' | 'DQ Engineer';

export interface DqPersonaTask {
  id: string;
  persona: DqPersona;
  title: string;
  stage: string;
  priority: 'High' | 'Medium' | 'Low';
  description: string;
  due: string;
}

export interface DqDimensionRow {
  id: string;
  code: string;
  name: string;
  definition: string;
  version: string;
  status: string;
  owner: string;
  lastUpdated: string;
  actions: string[];
}

export interface DqEdeMappingRow {
  edeId: string;
  edeName: string;
  edeDefinition: string;
  cdeId: string;
  cdeName: string;
  systemName: string;
  databaseName: string;
  attribute: string;
  status: string;
}

export interface DqBusinessRuleRow {
  id: string;
  edeId: string;
  edeName: string;
  dqDimension: string;
  input: string;
  objective: string;
  ruleDefinition: string;
  guidelines: string;
  acceptanceCriteria: string;
  status: string;
  owner: string;
  actions: string[];
}

export interface DqTechnicalRuleRow {
  id: string;
  edeId: string;
  edeName: string;
  dqDimension: string;
  cdeIds: string[];
  cdeNames: string[];
  businessRule: string;
  technicalRule: string;
  version: string;
  status: string;
  implementationTarget: string;
  actions: string[];
}

export interface DqOutcomeRow {
  id: string;
  dqDimension: string;
  edeName: string;
  passRate: number;
  trend: 'Up' | 'Flat' | 'Down';
  issueCount: number;
  lastRun: string;
  platform: string;
}

export const personas: DqPersona[] = ['Central CDO', 'BU CDO', 'DQ Analyst', 'DQ Engineer'];

export const personaTasks: DqPersonaTask[] = [
  {
    id: 'task-1',
    persona: 'Central CDO',
    title: 'Approve customer completeness rules',
    stage: 'Central approval',
    priority: 'High',
    description: 'Two business rules are waiting after BU CDO review for Customer Golden Record.',
    due: 'Today',
  },
  {
    id: 'task-2',
    persona: 'BU CDO',
    title: 'Review generated KYC business rules',
    stage: 'BU approval',
    priority: 'High',
    description: 'DQ Analyst generated three rules for KYC onboarding quality checks.',
    due: 'Tomorrow',
  },
  {
    id: 'task-3',
    persona: 'DQ Analyst',
    title: 'Generate technical rules from approved dimensions',
    stage: 'Rule generation',
    priority: 'Medium',
    description: 'Translate approved business rules for Product Reference Data into executable controls.',
    due: 'This week',
  },
  {
    id: 'task-4',
    persona: 'DQ Engineer',
    title: 'Implement AML threshold rule in dbt',
    stage: 'Implementation',
    priority: 'High',
    description: 'Technical rule approved and ready for dbt pipeline deployment.',
    due: 'Today',
  },
];

export const dimensions: DqDimensionRow[] = [
  {
    id: 'DQD-001',
    code: 'COMPLETENESS',
    name: 'Completeness',
    definition: 'Measures whether required fields exist and are populated across critical data elements.',
    version: 'v3',
    status: 'Approved',
    owner: 'Central CDO',
    lastUpdated: '2 hours ago',
    actions: ['Generate', 'Edit', 'Approve'],
  },
  {
    id: 'DQD-002',
    code: 'ACCURACY',
    name: 'Accuracy',
    definition: 'Measures whether the data stored matches the expected authoritative source values.',
    version: 'v2',
    status: 'Pending approval',
    owner: 'BU CDO',
    lastUpdated: 'Yesterday',
    actions: ['Generate', 'Edit', 'Approve'],
  },
  {
    id: 'DQD-003',
    code: 'CONSISTENCY',
    name: 'Consistency',
    definition: 'Measures whether related attributes remain aligned across systems, products, and channels.',
    version: 'v1',
    status: 'Draft',
    owner: 'DQ Analyst',
    lastUpdated: '3 days ago',
    actions: ['Generate', 'Edit'],
  },
];

export const edeMappings: DqEdeMappingRow[] = [
  {
    edeId: 'EDE-101',
    edeName: 'Customer Date of Birth',
    edeDefinition: 'Customer birth date used for identity verification and eligibility checks.',
    cdeId: 'CDE-2201',
    cdeName: 'customer_dob',
    systemName: 'Client 360',
    databaseName: 'gold_customer',
    attribute: 'dob',
    status: 'Validated',
  },
  {
    edeId: 'EDE-118',
    edeName: 'Primary Email Address',
    edeDefinition: 'Primary contact email used for customer communications and service notices.',
    cdeId: 'CDE-5410',
    cdeName: 'email_primary',
    systemName: 'CRM',
    databaseName: 'customer_profile',
    attribute: 'email_address',
    status: 'Mapped',
  },
  {
    edeId: 'EDE-203',
    edeName: 'AML Risk Score',
    edeDefinition: 'Latest AML risk assessment score assigned through the monitoring engine.',
    cdeId: 'CDE-7712',
    cdeName: 'risk_score',
    systemName: 'AML Monitoring',
    databaseName: 'aml_curated',
    attribute: 'risk_score',
    status: 'Uploaded',
  },
];

export const businessRules: DqBusinessRuleRow[] = [
  {
    id: 'DQB-041',
    edeId: 'EDE-101',
    edeName: 'Customer Date of Birth',
    dqDimension: 'Completeness',
    input: 'Customer onboarding records',
    objective: 'Ensure every onboarded customer has a valid date of birth.',
    ruleDefinition: 'DOB must be present for every individual customer record before activation.',
    guidelines: 'Use business glossary definitions and exclude legal entities.',
    acceptanceCriteria: '99.5% non-null over rolling 7-day window.',
    status: 'Pending BU CDO',
    owner: 'DQ Analyst',
    actions: ['Generate', 'Edit', 'Approve'],
  },
  {
    id: 'DQB-055',
    edeId: 'EDE-118',
    edeName: 'Primary Email Address',
    dqDimension: 'Accuracy',
    input: 'CRM profile master',
    objective: 'Ensure the mastered email reflects the latest verified source.',
    ruleDefinition: 'Primary email must match the verified channel preference record.',
    guidelines: 'Cross-check with consented communication channel feed.',
    acceptanceCriteria: '98% match rate against the consent service.',
    status: 'Pending Central CDO',
    owner: 'BU CDO',
    actions: ['Edit', 'Approve'],
  },
  {
    id: 'DQB-063',
    edeId: 'EDE-203',
    edeName: 'AML Risk Score',
    dqDimension: 'Consistency',
    input: 'AML scoring output and case management feed',
    objective: 'Keep AML score aligned between monitoring and case workflows.',
    ruleDefinition: 'The latest risk score must match across AML monitoring and case management within one hour.',
    guidelines: 'Consistency and accuracy rules may require comparison of two mapped CDEs.',
    acceptanceCriteria: 'Less than 0.5% mismatch rate across linked records.',
    status: 'Draft',
    owner: 'DQ Analyst',
    actions: ['Generate', 'Edit'],
  },
];

export const technicalRules: DqTechnicalRuleRow[] = [
  {
    id: 'DQT-014',
    edeId: 'EDE-101',
    edeName: 'Customer Date of Birth',
    dqDimension: 'Completeness',
    cdeIds: ['CDE-2201'],
    cdeNames: ['customer_dob'],
    businessRule: 'DOB must exist before activation.',
    technicalRule: "customer_dob IS NOT NULL AND customer_status = 'ACTIVE'",
    version: 'v2',
    status: 'Approved',
    implementationTarget: 'dbt',
    actions: ['Generate', 'Edit', 'Approve', 'Implement'],
  },
  {
    id: 'DQT-029',
    edeId: 'EDE-118',
    edeName: 'Primary Email Address',
    dqDimension: 'Accuracy',
    cdeIds: ['CDE-5410', 'CDE-5419'],
    cdeNames: ['email_primary', 'verified_email'],
    businessRule: 'Primary email must match verified source.',
    technicalRule: 'LOWER(email_primary) = LOWER(verified_email)',
    version: 'v1',
    status: 'Pending approval',
    implementationTarget: 'SQL',
    actions: ['Generate', 'Edit', 'Approve'],
  },
  {
    id: 'DQT-032',
    edeId: 'EDE-203',
    edeName: 'AML Risk Score',
    dqDimension: 'Consistency',
    cdeIds: ['CDE-7712', 'CDE-9904'],
    cdeNames: ['risk_score', 'case_risk_score'],
    businessRule: 'Scores must match between AML systems.',
    technicalRule: 'risk_score = case_risk_score',
    version: 'v1',
    status: 'Implemented',
    implementationTarget: 'PySpark',
    actions: ['Edit', 'Implement'],
  },
];

export const outcomes: DqOutcomeRow[] = [
  {
    id: 'OUT-1',
    dqDimension: 'Completeness',
    edeName: 'Customer Date of Birth',
    passRate: 99.4,
    trend: 'Up',
    issueCount: 17,
    lastRun: 'Today, 06:00 UTC',
    platform: 'dbt',
  },
  {
    id: 'OUT-2',
    dqDimension: 'Accuracy',
    edeName: 'Primary Email Address',
    passRate: 97.9,
    trend: 'Flat',
    issueCount: 43,
    lastRun: 'Today, 06:15 UTC',
    platform: 'SQL',
  },
  {
    id: 'OUT-3',
    dqDimension: 'Consistency',
    edeName: 'AML Risk Score',
    passRate: 96.1,
    trend: 'Down',
    issueCount: 89,
    lastRun: 'Today, 05:45 UTC',
    platform: 'PySpark',
  },
];

export const implementationTargets = ['dbt', 'SQL', 'PySpark'];