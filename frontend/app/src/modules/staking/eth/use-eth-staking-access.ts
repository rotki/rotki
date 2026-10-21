import type { Ref } from 'vue';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';

interface UseEthStakingAccessReturn {
  enabled: Readonly<Ref<boolean>>;
  module: Module;
  allowed: Readonly<Ref<boolean>>;
  available: Readonly<Ref<boolean>>;
}

/**
 * Whether the ETH staking page may show and load staking data.
 *
 * @remarks
 * `available` needs both the premium tier (`allowed`) and the eth2 module (`enabled`). The page
 * renders a gate for either one missing, so nothing behind it may load: the staking performance
 * fetch asserts premium.
 */
export function useEthStakingAccess(): UseEthStakingAccessReturn {
  const module = Module.ETH2;

  const { enabled } = useModuleEnabled(module);

  const { allowed } = useFeatureAccess(PremiumFeature.ETH_STAKING_VIEW);

  const available = logicAnd(allowed, enabled);

  return {
    allowed,
    available,
    enabled,
    module,
  };
}
