import { defaultAccountingSettings } from '@/data/factories';
import { type AccountingSettings } from '@/types/user';

export const useAccountingSettingsStore = defineStore(
  'settings/accounting',
  () => {
    const settings = reactive(defaultAccountingSettings());

    const pnlCsvHaveSummary = computed(() => settings.pnlCsvHaveSummary);
    const pnlCsvWithFormulas = computed(() => settings.pnlCsvWithFormulas);
    const includeCrypto2crypto = computed(() => settings.includeCrypto2crypto);
    const includeGasCosts = computed(() => settings.includeGasCosts);
    const taxfreeAfterPeriod = computed(() => settings.taxfreeAfterPeriod);
    const accountForAssetsMovements = computed(
      () => settings.accountForAssetsMovements
    );
    const calculatePastCostBasis = computed(
      () => settings.calculatePastCostBasis
    );
    const ethStakingTaxableAfterWithdrawalEnabled = computed(
      () => settings.ethStakingTaxableAfterWithdrawalEnabled
    );
    const costBasisMethod = computed(() => settings.costBasisMethod);

    const update = (accountingSettings: AccountingSettings): void => {
      Object.assign(settings, accountingSettings);
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
      costBasisMethod,
      // return settings on development for state persistence
      ...(checkIfDevelopment() ? { settings } : {}),
      update
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAccountingSettingsStore, import.meta.hot)
  );
}
