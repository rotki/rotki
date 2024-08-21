import { defaultAccountingSettings } from '@/data/factories';
import type { AccountingSettings } from '@/types/user';

export const useAccountingSettingsStore = defineStore('settings/accounting', () => {
  const settings = ref(defaultAccountingSettings());

  const pnlCsvHaveSummary = useComputedRef(settings, 'pnlCsvHaveSummary');
  const pnlCsvWithFormulas = useComputedRef(settings, 'pnlCsvWithFormulas');
  const includeCrypto2crypto = useComputedRef(settings, 'includeCrypto2crypto');
  const includeFeesInCostBasis = useComputedRef(settings, 'includeFeesInCostBasis');
  const includeGasCosts = useComputedRef(settings, 'includeGasCosts');
  const taxfreeAfterPeriod = useComputedRef(settings, 'taxfreeAfterPeriod');
  const accountForAssetsMovements = useComputedRef(settings, 'accountForAssetsMovements');
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
    pnlCsvHaveSummary,
    pnlCsvWithFormulas,
    includeCrypto2crypto,
    includeGasCosts,
    taxfreeAfterPeriod,
    accountForAssetsMovements,
    calculatePastCostBasis,
    ethStakingTaxableAfterWithdrawalEnabled,
    includeFeesInCostBasis,
    costBasisMethod,
    settings,
    update,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAccountingSettingsStore, import.meta.hot));
