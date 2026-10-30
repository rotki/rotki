import type { ComputedRef } from 'vue';
import { LidoCsmStakingModule } from '@/modules/staking/lido-csm/constants';

interface LidoCsmStakingModuleOption {
  key: LidoCsmStakingModule;
  label: string;
}

interface UseLidoCsmStakingModulesReturn {
  stakingModuleOptions: ComputedRef<LidoCsmStakingModuleOption[]>;
  stakingModuleLabel: (stakingModuleId: number) => string;
}

export function useLidoCsmStakingModules(): UseLidoCsmStakingModulesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const stakingModuleOptions = computed<LidoCsmStakingModuleOption[]>(() => [{
    key: LidoCsmStakingModule.CSM,
    label: t('staking_page.lido_csm.modules.csm'),
  }, {
    key: LidoCsmStakingModule.CSM_0X02,
    label: t('staking_page.lido_csm.modules.csm_0x02'),
  }]);

  /**
   * The name of a module the backend reported.
   *
   * @remarks
   * An id this frontend does not know yet is shown as the bare id, so the row stays distinguishable.
   */
  function stakingModuleLabel(stakingModuleId: number): string {
    return get(stakingModuleOptions).find(option => option.key === stakingModuleId)?.label ?? String(stakingModuleId);
  }

  return {
    stakingModuleLabel,
    stakingModuleOptions,
  };
}
