import type { ComputedRef, Ref } from 'vue';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import { Module } from '@/types/modules';

interface UseEthStakingAccessReturn {
  enabled: ComputedRef<boolean>;
  module: Module;
  premium: Ref<boolean>;
}

export function useEthStakingAccess(): UseEthStakingAccessReturn {
  const module = Module.ETH2;

  const { isModuleEnabled } = useModules();
  const premium = usePremium();

  const enabled = isModuleEnabled(module);

  return {
    enabled,
    module,
    premium,
  };
}
