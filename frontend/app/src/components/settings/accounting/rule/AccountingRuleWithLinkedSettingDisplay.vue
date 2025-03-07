<script setup lang="ts">
import type { AccountingRuleWithLinkedProperty } from '@/types/settings/accounting';
import SuccessDisplay from '@/components/display/SuccessDisplay.vue';
import { useAccountingRuleMappings } from '@/composables/settings/accounting/rule-mapping';

const props = defineProps<{
  identifier: string;
  item: AccountingRuleWithLinkedProperty;
}>();

const { identifier, item } = toRefs(props);

const { t } = useI18n();

const { accountingRuleLinkedMappingData } = useAccountingRuleMappings();

const linkableSettingOptions = accountingRuleLinkedMappingData(identifier);

const selectedLinkableSetting = computed(() => {
  const itemVal = get(item);
  const linkedProperty = itemVal.linkedSetting;
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

  return get(item).value;
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
