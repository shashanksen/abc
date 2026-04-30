/**
 * Frontend mirror of backend error codes.
 *
 * The backend returns: { error: { code, message, detail, context } }
 * We parse it into ApiError, then UI components show user-friendly messages.
 */

export interface ApiErrorPayload {
  code: string;
  message: string;
  detail?: string | null;
  context?: Record<string, unknown>;
}

export class ApiError extends Error {
  code: string;
  detail?: string | null;
  context?: Record<string, unknown>;
  httpStatus: number;

  constructor(httpStatus: number, payload: ApiErrorPayload) {
    super(payload.message);
    this.code = payload.code;
    this.detail = payload.detail;
    this.context = payload.context;
    this.httpStatus = httpStatus;
  }

  /** Friendly message for end-users (override per code if needed). */
  userMessage(): string {
    const friendly: Record<string, string> = {
      'CDP-AUT-0001': 'Email or password is incorrect.',
      'CDP-AUT-0002': 'Your session has expired. Please log in again.',
      'CDP-AUT-0003': 'Your session is invalid. Please log in again.',
      'CDP-AUT-0004': 'Your account is disabled. Contact an administrator.',
      'CDP-AUT-0005': 'An account with that email already exists.',
      'CDP-AUT-0006': 'Please log in to continue.',
      'CDP-ACC-0030': "You don't have permission for this action.",
      'CDP-ACC-0031': "You don't have access to this module.",
      'CDP-ACC-0034': 'You already have a pending request for this module.',
      'CDP-ACC-0035': 'Admin privilege required.',
    };
    return friendly[this.code] || this.message;
  }
}
