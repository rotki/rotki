import type { Ref } from 'vue';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';

interface UseEthStakingAccessReturn {
  enabled: Readonly<Ref<boolean>>;
  module: Module;
  allowed: Readonly<Ref<boolean>>;
}

export function useEthStakingAccess(): UseEthStakingAccessReturn {
  const module = Module.ETH2;

  const { enabled } = useModuleEnabled(module);

  const { allowed } = useFeatureAccess(PremiumFeature.ETH_STAKING_VIEW);

  return {
    allowed,
    enabled,
    module,
  };
}
