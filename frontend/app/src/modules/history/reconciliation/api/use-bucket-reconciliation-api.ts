import { api } from '@/modules/core/api/rotki-api';
import {
  type ReconciliationAccount,
  type ReconciliationRequest,
  type ReconciliationResponse,
  ReconciliationResponse as ReconciliationResponseSchema,
} from '@/modules/history/reconciliation/schemas';

const BASE = '/balances/historical/reconciliation';

/** The most rows one expanded account can hold. */
export const MAX_ACCOUNT_BUCKETS = 500;

/** The rows an expanded account asks for first. */
export const ACCOUNT_PAGE_SIZE = 50;

function queryFor(request: ReconciliationRequest): Record<string, unknown> {
  return {
    location: request.location,
    locationLabel: request.locationLabel,
    status: request.status,
    limit: request.limit,
    offset: request.offset,
  };
}

export interface UseBucketReconciliationApiReturn {
  fetchSummary: () => Promise<ReconciliationResponse>;
  fetchAccount: (request: Required<Pick<ReconciliationRequest, 'location'>> & ReconciliationRequest) => Promise<ReconciliationAccount | undefined>;
}

/**
 * Reads the read-only reconciliation report.
 *
 * @remarks
 * The account request is the same resource with `location` and `location_label`, which is the only
 * pair that makes the backend include bucket rows. Null amounts and null timestamps stay null:
 * turning either into zero would invent a balance the backend could not observe.
 */
export function useBucketReconciliationApi(): UseBucketReconciliationApiReturn {
  const fetchSummary = async (): Promise<ReconciliationResponse> => {
    const response = await api.get<unknown>(BASE, { query: queryFor({}) });
    return ReconciliationResponseSchema.parse(response);
  };

  const fetchAccount = async (
    request: Required<Pick<ReconciliationRequest, 'location'>> & ReconciliationRequest,
  ): Promise<ReconciliationAccount | undefined> => {
    const response = ReconciliationResponseSchema.parse(await api.get<unknown>(BASE, { query: queryFor(request) }));
    // The empty label is the explicit scope for a null-keyed account; the response reports null.
    const requestedLabel = request.locationLabel?.length ? request.locationLabel : null;
    return response.accounts.find(account => account.location === request.location
      && (account.locationLabel ?? null) === requestedLabel);
  };

  return {
    fetchAccount,
    fetchSummary,
  };
}
