import type { MaybeRefOrGetter } from 'vue';
import type { AccountingRuleLinkedSettingMap } from '@/modules/settings/types/accounting';
import { assert, toHumanReadable, transformCase } from '@rotki/common';
import { useAccountingApi } from '@/modules/settings/api/use-accounting-api';
import { settingsRegistry } from '@/modules/settings/settings-registry';
import { type SettingKey, useSetting } from '@/modules/settings/use-setting';

export const useAccountingRuleMappings = createSharedComposable(() => {
  // eslint-disable-next-line @typescript-eslint/unbound-method
  const { t, te } = useI18n({ useScope: 'global' });

  const { getAccountingRuleLinkedMapping } = useAccountingApi();

  const accountingRuleLinkedMapping: Ref<Record<string, string[]>> = computedAsync(
    async () => getAccountingRuleLinkedMapping(),
    {},
  );

  const stateInStore = (stateName: string): stateName is SettingKey => stateName in settingsRegistry;

  const stateIsBoolean = (state: MaybeRef<any>): state is MaybeRef<boolean> => typeof get(state) === 'boolean';

  const accountingRuleLinkedMappingData = (key: MaybeRefOrGetter<string>): ComputedRef<AccountingRuleLinkedSettingMap[]> =>
    computed(() => {
      const data = get(accountingRuleLinkedMapping)[toValue(key)];

      if (!data)
        return [];

      const result: AccountingRuleLinkedSettingMap[] = [];

      data.forEach((item) => {
        const translationKey = `accounting_settings.trade.labels.${item}`;
        const stateName = transformCase(item, true);

        assert(stateInStore(stateName), `linked property ${stateName} is not part of the setting`);
        const state = useSetting(stateName);

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
