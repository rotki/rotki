import { isUnreachable } from '@/modules/core/api/request-result';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';

/**
 * Names a failed request for the user, wherever it is shown in place of the data.
 *
 * @remarks
 * The backend's own message where it answered; when the request got no response at all, a sentence
 * saying so, since ofetch's message for that case is the raw request line.
 */
export function useFailureMessage(): (failure: unknown) => string {
  const { t } = useI18n({ useScope: 'global' });
  return (failure: unknown): string => (isUnreachable(failure) ? t('common.backend_unreachable') : getErrorMessage(failure));
}
