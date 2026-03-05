import type { Ref } from 'vue';
import { Module, useModuleEnabled } from '@/composables/session/modules';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';

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
