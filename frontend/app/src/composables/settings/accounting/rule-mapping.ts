import type { MaybeRef } from '@vueuse/core';
import type { AccountingRuleLinkedSettingMap } from '@/types/settings/accounting';
import { assert, toHumanReadable, transformCase } from '@rotki/common';
import { useAccountingApi } from '@/composables/api/settings/accounting-api';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

export const useAccountingRuleMappings = createSharedComposable(() => {
  // eslint-disable-next-line @typescript-eslint/unbound-method
  const { t, te } = useI18n({ useScope: 'global' });

  const { getAccountingRuleLinkedMapping } = useAccountingApi();

  const accountingRuleLinkedMapping: Ref<Record<string, string[]>> = asyncComputed(
    async () => getAccountingRuleLinkedMapping(),
    {},
  );

  const store = storeToRefs(useAccountingSettingsStore());

  const stateInStore = (stateName: string): stateName is keyof typeof store => stateName in store;

  const stateIsBoolean = (state: MaybeRef<any>): state is MaybeRef<boolean> => typeof get(state) === 'boolean';

  const accountingRuleLinkedMappingData = (key: MaybeRef<string>): ComputedRef<AccountingRuleLinkedSettingMap[]> =>
    computed(() => {
      const data = get(accountingRuleLinkedMapping)[get(key)];

      if (!data)
        return [];

      const result: AccountingRuleLinkedSettingMap[] = [];

      data.forEach((item) => {
        const translationKey = `accounting_settings.trade.labels.${item}`;
        const stateName = transformCase(item, true);

        assert(stateInStore(stateName), `linked property ${stateName} is not part of the setting`);
        const state = store[stateName];

        assert(stateIsBoolean(state), `linked property ${stateName} is not boolean`);

        const label = te(translationKey) ? t(translationKey) : toHumanReadable(item);

        result.push({
          identifier: item,
          label,
          state: get(state),
        });
      });

      return result;
    });

  return {
    accountingRuleLinkedMappingData,
  };
});
