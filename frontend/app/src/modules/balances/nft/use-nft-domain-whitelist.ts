import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { startPromise } from '@shared/utils';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { getDomain } from '@/modules/core/common/helpers/url';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface UseNftDomainWhitelistReturn {
  /** The registrable domain the NFT media is served from; empty when there is no media URL. */
  domain: ComputedRef<string>;
  /** Asks the user to confirm, then adds `domain` to the domains whose NFT media is rendered. */
  confirmAllowDomain: () => void;
}

/**
 * Lets the user allow the domain of an NFT's media, so its image renders instead of a placeholder.
 *
 * @param mediaUrl - the NFT's image or video URL
 */
export function useNftDomainWhitelist(mediaUrl: MaybeRefOrGetter<string | null>): UseNftDomainWhitelistReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { show } = useConfirmStore();
  const whitelistedDomainsForNftImages = useSetting('whitelistedDomainsForNftImages');
  const { updateFrontendSetting } = useSettingsOperations();

  const domain = computed<string>(() => getDomain(toValue(mediaUrl) ?? ''));

  function allowDomain(): void {
    const domainVal = get(domain);
    if (!domainVal)
      return;

    const whitelisted = [...get(whitelistedDomainsForNftImages), domainVal].filter(uniqueStrings);
    startPromise(updateFrontendSetting({ whitelistedDomainsForNftImages: whitelisted }));
  }

  function confirmAllowDomain(): void {
    show(
      {
        message: t('general_settings.nft_setting.update_whitelist_confirmation.message', { domain: get(domain) }, 2),
        title: t('general_settings.nft_setting.update_whitelist_confirmation.title'),
      },
      allowDomain,
    );
  }

  return {
    confirmAllowDomain,
    domain,
  };
}
