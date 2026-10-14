import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { logger } from '@/modules/core/common/logging/logging';
import { useFrontendSettingsWriter } from '@/modules/settings/use-frontend-settings-writer';
import { useSetting } from '@/modules/settings/use-setting';

export type ApiKeyNoticeService = 'etherscan' | 'helius' | 'beaconchain' | 'consensusRpc' | 'blockscout';

interface UseApiKeyNoticeReturn {
  /** Whether the user asked to stop being reminded about this key. */
  dismissed: ComputedRef<boolean>;
  dismiss: () => Promise<void>;
}

/**
 * The remembered "stop reminding me" for an optional API key.
 *
 * An optional key is an offer rather than a fault, so the reminder can be put away, and the choice
 * is a frontend setting so it survives a reload.
 */
export function useApiKeyNotice(service: MaybeRefOrGetter<ApiKeyNoticeService | undefined>): UseApiKeyNoticeReturn {
  const dismissedNotices = useSetting('dismissedApiKeyNotices');
  const { updateFrontendSetting } = useFrontendSettingsWriter();

  const dismissed = computed<boolean>(() => {
    const value = toValue(service);
    return !!value && get(dismissedNotices).includes(value);
  });

  async function dismiss(): Promise<void> {
    const value = toValue(service);
    const current = get(dismissedNotices);
    if (!value || current.includes(value))
      return;

    const status = await updateFrontendSetting({ dismissedApiKeyNotices: [...current, value] });
    if (!status.success)
      logger.error(`failed to dismiss the ${value} api key notice: ${status.message}`);
  }

  return {
    dismiss,
    dismissed,
  };
}
