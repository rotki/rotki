import { defaultAccountingSettings } from '@/data/factories';
import { AccountingSettings } from '@/types/user';

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
    const taxableLedgerActions = computed(() => settings.taxableLedgerActions);
    const ethStakingTaxableAfterWithdrawalEnabled = computed(
      () => settings.ethStakingTaxableAfterWithdrawalEnabled
    );
    const costBasisMethod = computed(() => settings.costBasisMethod);

    const update = (accountingSettings: AccountingSettings) => {
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
      taxableLedgerActions,
      ethStakingTaxableAfterWithdrawalEnabled,
      costBasisMethod,
      update
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAccountingSettingsStore, import.meta.hot)
  );
}
