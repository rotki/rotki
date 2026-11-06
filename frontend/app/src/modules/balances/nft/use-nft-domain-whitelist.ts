import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { startPromise } from '@shared/utils';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { getDomain } from '@/modules/core/common/helpers/url';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface UseNftDomainWhitelistReturn {
  /** The registrable domain the NFT media is served from; empty when there is no media URL. */
  domain: ComputedRef<string>;
  /** What to ask beside the control that allows the domain, before `allowDomain` runs. */
  question: ComputedRef<ConfirmQuestion>;
  /** Adds `domain` to the domains whose NFT media is rendered; call it once the user accepted. */
  allowDomain: () => void;
}

/**
 * Lets the user allow the domain of an NFT's media, so its image renders instead of a placeholder.
 *
 * @param mediaUrl - the NFT's image or video URL
 */
export function useNftDomainWhitelist(mediaUrl: MaybeRefOrGetter<string | null>): UseNftDomainWhitelistReturn {
  const { t } = useI18n({ useScope: 'global' });
  const whitelistedDomainsForNftImages = useSetting('whitelistedDomainsForNftImages');
  const { updateFrontendSetting } = useSettingsOperations();

  const domain = computed<string>(() => getDomain(toValue(mediaUrl) ?? ''));

  const question = computed<ConfirmQuestion>(() => ({
    confirmLabel: t('general_settings.nft_setting.update_whitelist_confirmation.confirm'),
    message: t('general_settings.nft_setting.update_whitelist_confirmation.message', { domain: get(domain) }, 2),
    title: t('general_settings.nft_setting.update_whitelist_confirmation.title'),
  }));

  function allowDomain(): void {
    const domainVal = get(domain);
    if (!domainVal)
      return;

    const whitelisted = [...get(whitelistedDomainsForNftImages), domainVal].filter(uniqueStrings);
    startPromise(updateFrontendSetting({ whitelistedDomainsForNftImages: whitelisted }));
  }

  return {
    allowDomain,
    domain,
    question,
  };
}
