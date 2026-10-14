<script setup lang="ts">
import type { AccountingRuleWithLinkedProperty } from '@/modules/settings/types/accounting';
import { useAccountingRuleMappings } from '@/modules/settings/accounting/use-accounting-rule-mappings';
import SuccessDisplay from '@/modules/shell/components/display/SuccessDisplay.vue';

const { identifier, item } = defineProps<{
  identifier: string;
  item: AccountingRuleWithLinkedProperty;
}>();

const { t } = useI18n({ useScope: 'global' });

const { accountingRuleLinkedMappingData } = useAccountingRuleMappings();

const linkableSettingOptions = accountingRuleLinkedMappingData(() => identifier);

const selectedLinkableSetting = computed(() => {
  const linkedProperty = item.linkedSetting;
  if (linkedProperty) {
    const foundItem = get(linkableSettingOptions).find(item => item.identifier === linkedProperty);

    if (foundItem)
      return foundItem;
  }

  return null;
});

const value = computed<boolean>(() => {
  const selectedLinkableSettingVal = get(selectedLinkableSetting);
  if (selectedLinkableSettingVal)
    return get(selectedLinkableSettingVal).state;

  return item.value;
});
</script>

<template>
  <span class="inline-flex items-center gap-1.5">
    <SuccessDisplay
      size="20"
      :success="value"
    />
    <RuiTooltip
      v-if="selectedLinkableSetting"
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <span
          class="inline-flex items-center gap-1 text-xs text-rui-text-secondary whitespace-nowrap"
          data-testid="accounting-rule-linked-setting"
        >
          <RuiIcon
            size="12"
            name="lu-link"
          />
          {{ selectedLinkableSetting.label }}
        </span>
      </template>
      {{ t('accounting_settings.rule.value_overwritten') }}
    </RuiTooltip>
  </span>
</template>
