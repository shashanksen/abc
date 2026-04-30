import { BaseApiClient } from '@/lib/apiClient';

export interface Dimension {
  id: string;
  code: string;
  name: string;
  definition: string;
  version: number;
  status: 'DRAFT' | 'ACTIVE' | 'RETIRED';
  created_at: string;
  updated_at: string;
}

export interface BusinessRule {
  id: string;
  code: string;
  dimension_id?: string | null;
  ede_mapping?: string | null;
  rule_text: string;
  version: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TechnicalRule {
  id: string;
  code: string;
  dimension_id?: string | null;
  ede?: string | null;
  cde?: string | null;
  attribute?: string | null;
  rule_expr: string;
  status: string;
  created_at: string;
  updated_at: string;
}

class DqApi extends BaseApiClient {
  // Dimensions
  listDimensions()                                   { return this.get<Dimension[]>('/dq/dimensions'); }
  createDimension(d: { code: string; name: string; definition: string }) {
    return this.post<Dimension>('/dq/dimensions', d);
  }
  updateDimension(id: string, d: Partial<Pick<Dimension, 'name' | 'definition' | 'status'>>) {
    return this.patch<Dimension>(`/dq/dimensions/${id}`, d);
  }

  // Business rules
  listBusinessRules()                                { return this.get<BusinessRule[]>('/dq/business-rules'); }
  createBusinessRule(d: { code: string; dimension_id?: string; ede_mapping?: string; rule_text: string }) {
    return this.post<BusinessRule>('/dq/business-rules', d);
  }

  // Technical rules
  listTechnicalRules()                               { return this.get<TechnicalRule[]>('/dq/technical-rules'); }
  createTechnicalRule(d: { code: string; dimension_id?: string; ede?: string; cde?: string; attribute?: string; rule_expr: string }) {
    return this.post<TechnicalRule>('/dq/technical-rules', d);
  }
}

export const dqApi = new DqApi();
