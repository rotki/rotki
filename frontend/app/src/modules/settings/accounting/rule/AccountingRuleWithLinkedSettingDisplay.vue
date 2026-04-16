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
  <RuiBadge
    placement="top"
    size="sm"
    color="secondary"
    class="[&_span]:!px-0"
    :model-value="!!selectedLinkableSetting"
  >
    <template #icon>
      <RuiTooltip
        v-if="selectedLinkableSetting"
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiIcon
            size="12"
            name="lu-link"
          />
        </template>
        <div>{{ t('accounting_settings.rule.value_overwritten') }}</div>
        <div class="font-bold">
          {{ selectedLinkableSetting.label }}
        </div>
      </RuiTooltip>
    </template>
    <SuccessDisplay
      size="28"
      :success="value"
    />
  </RuiBadge>
</template>
