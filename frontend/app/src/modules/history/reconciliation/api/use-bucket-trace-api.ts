import { api } from '@/modules/core/api/rotki-api';
import {
  type BucketTraceRequest,
  type BucketTraceResponse,
  BucketTraceResponse as BucketTraceResponseSchema,
} from '@/modules/history/reconciliation/schemas';

const BUCKET_TRACE_ENDPOINT = '/data_issues/diagnostics/bucket_trace';

/** Default page size for the bucket trace drawer. */
export const BUCKET_TRACE_PAGE_SIZE = 50;

export interface UseBucketTraceApiReturn {
  fetchBucketTrace: (request: BucketTraceRequest) => Promise<BucketTraceResponse>;
}

/** Reads the chronological event trace of one historical-balance bucket. */
export function useBucketTraceApi(): UseBucketTraceApiReturn {
  const fetchBucketTrace = async (request: BucketTraceRequest): Promise<BucketTraceResponse> => {
    const payload: Record<string, unknown> = {
      asset: request.asset,
      limit: request.limit ?? BUCKET_TRACE_PAGE_SIZE,
      location: request.location,
    };
    if (request.locationLabel)
      payload.locationLabel = request.locationLabel;
    if (request.protocol)
      payload.protocol = request.protocol;
    if (request.offset !== undefined)
      payload.offset = request.offset;

    const response = await api.post<unknown>(BUCKET_TRACE_ENDPOINT, payload);
    return BucketTraceResponseSchema.parse(response);
  };

  return { fetchBucketTrace };
}
