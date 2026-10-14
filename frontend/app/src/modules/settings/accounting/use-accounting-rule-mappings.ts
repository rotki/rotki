import type { MaybeRefOrGetter } from 'vue';
import type { AccountingRuleLinkedSettingMap } from '@/modules/settings/types/accounting';
import { assert, toHumanReadable, transformCase } from '@rotki/common';
import { type MessageKey, msg } from '@/message-key';
import { useAccountingApi } from '@/modules/settings/api/use-accounting-api';
import { settingsRegistry } from '@/modules/settings/settings-registry';
import { type SettingKey, useSetting } from '@/modules/settings/use-setting';

/**
 * Short names for the settings a rule can follow, keyed by the identifier the backend sends. An
 * identifier missing here still works: it shows as a readable form of itself.
 */
const LINKED_SETTING_TITLES: Partial<Record<string, MessageKey>> = {
  calculate_past_cost_basis: msg.$t('accounting_settings.trade.titles.calculate_past_cost_basis'),
  eth_staking_taxable_after_withdrawal_enabled: msg.$t('accounting_settings.trade.titles.eth_staking_taxable_after_withdrawal_enabled'),
  include_crypto2crypto: msg.$t('accounting_settings.trade.titles.include_crypto2crypto'),
  include_fees_in_cost_basis: msg.$t('accounting_settings.trade.titles.include_fees_in_cost_basis'),
  include_gas_costs: msg.$t('accounting_settings.trade.titles.include_gas_costs'),
  use_asset_collections_in_cost_basis: msg.$t('accounting_settings.trade.titles.use_asset_collections_in_cost_basis'),
};

export const useAccountingRuleMappings = createSharedComposable(() => {
  const { t } = useI18n({ useScope: 'global' });

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
        const stateName = transformCase(item, true);

        assert(stateInStore(stateName), `linked property ${stateName} is not part of the setting`);
        const state = useSetting(stateName);

        assert(stateIsBoolean(state), `linked property ${stateName} is not boolean`);

        const titleKey = LINKED_SETTING_TITLES[item];
        const label = titleKey ? t(titleKey) : toHumanReadable(item);

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
