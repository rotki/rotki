import { Status } from '@/types/status';

/**
 * Returns true if a section is loading
 *
 * @deprecated use useStatusUpdater#loading instead
 * @param status
 */
export function isLoading(status: Status): boolean {
  return (
    status === Status.LOADING ||
    status === Status.PARTIALLY_LOADED ||
    status === Status.REFRESHING
  );
}
