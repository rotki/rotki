import type { ComputedRef } from 'vue';
import { externalLinks } from '@shared/external-links';
import { usePremium } from '@/modules/premium/use-premium';

interface UsePlanUpgradeLinkReturn {
  /** The link label, the same for every plan so prompts can open a sentence with it. */
  upgradeText: ComputedRef<string>;
  /** Subscription management for a subscriber; `undefined` lets `ExternalLink` fall back to the premium page. */
  upgradeUrl: ComputedRef<string | undefined>;
}

export function usePlanUpgradeLink(): UsePlanUpgradeLinkReturn {
  const { t } = useI18n({ useScope: 'global' });
  const premium = usePremium();

  const upgradeText = computed<string>(() => t('plan_limit.upgrade'));

  const upgradeUrl = computed<string | undefined>(() => (get(premium) ? externalLinks.manageSubscriptions : undefined));

  return {
    upgradeText,
    upgradeUrl,
  };
}
