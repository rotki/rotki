import type { ComputedRef } from 'vue';
import { useModules } from '@/composables/session/modules';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { Module } from '@/types/modules';

interface UseEthStakingAccessReturn {
  enabled: ComputedRef<boolean>;
  module: Module;
  allowed: ComputedRef<boolean>;
}

export function useEthStakingAccess(): UseEthStakingAccessReturn {
  const module = Module.ETH2;

  const { isModuleEnabled } = useModules();

  const { allowed } = useFeatureAccess(PremiumFeature.ETH_STAKING_VIEW);

  const enabled = isModuleEnabled(module);

  return {
    allowed,
    enabled,
    module,
  };
}
