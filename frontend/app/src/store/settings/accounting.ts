import { defaultAccountingSettings } from '@/data/factories';
import { useComputedRef } from '@/composables/utils/useComputedRef';
import type { AccountingSettings } from '@/types/user';

export const useAccountingSettingsStore = defineStore('settings/accounting', () => {
  const settings = ref(defaultAccountingSettings());

  const pnlCsvHaveSummary = useComputedRef(settings, 'pnlCsvHaveSummary');
  const pnlCsvWithFormulas = useComputedRef(settings, 'pnlCsvWithFormulas');
  const includeCrypto2crypto = useComputedRef(settings, 'includeCrypto2crypto');
  const includeFeesInCostBasis = useComputedRef(settings, 'includeFeesInCostBasis');
  const includeGasCosts = useComputedRef(settings, 'includeGasCosts');
  const taxfreeAfterPeriod = useComputedRef(settings, 'taxfreeAfterPeriod');
  const calculatePastCostBasis = useComputedRef(settings, 'calculatePastCostBasis');
  const ethStakingTaxableAfterWithdrawalEnabled = useComputedRef(settings, 'ethStakingTaxableAfterWithdrawalEnabled');
  const costBasisMethod = useComputedRef(settings, 'costBasisMethod');

  const update = (accountingSettings: AccountingSettings): void => {
    set(settings, {
      ...get(settings),
      ...accountingSettings,
    });
  };

  return {
    calculatePastCostBasis,
    costBasisMethod,
    ethStakingTaxableAfterWithdrawalEnabled,
    includeCrypto2crypto,
    includeFeesInCostBasis,
    includeGasCosts,
    pnlCsvHaveSummary,
    pnlCsvWithFormulas,
    settings,
    taxfreeAfterPeriod,
    update,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAccountingSettingsStore, import.meta.hot));
