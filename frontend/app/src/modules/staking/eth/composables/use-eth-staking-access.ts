import type { ComputedRef } from 'vue';
import { usePremiumHelper } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import { Module } from '@/types/modules';

interface UseEthStakingAccessReturn {
  enabled: ComputedRef<boolean>;
  module: Module;
  allowed: ComputedRef<boolean>;
}

export function useEthStakingAccess(): UseEthStakingAccessReturn {
  const module = Module.ETH2;

  const { isModuleEnabled } = useModules();

  const { isFeatureAllowed } = usePremiumHelper();

  const allowed = isFeatureAllowed('ethStakingView');

  const enabled = isModuleEnabled(module);

  return {
    allowed,
    enabled,
    module,
  };
}
