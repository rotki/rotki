<script setup lang="ts">
import { type AccountingRuleWithLinkedProperty } from '@/types/settings/accounting';

const props = defineProps<{
  identifier: string;
  value: AccountingRuleWithLinkedProperty;
  label: string;
  hint: string;
}>();

const emit = defineEmits<{
  (e: 'input', value: AccountingRuleWithLinkedProperty): void;
}>();

const { identifier, value } = toRefs(props);

const { t } = useI18n();

const input = (newValue: AccountingRuleWithLinkedProperty) => {
  emit('input', newValue);
};

const { accountingRuleLinkedMappingData } = useAccountingRuleMappings();

const linkableSettingOptions = accountingRuleLinkedMappingData(identifier);

const linkedModel = computed({
  get() {
    return !!get(value).linkedSetting;
  },
  set(newValue: boolean) {
    if (newValue) {
      input({
        value: get(value).value,
        linkedSetting: get(linkableSettingOptions)[0]?.identifier || ''
      });
    } else {
      input({
        value: get(value).value
      });
    }
  }
});

const linkedSettingModel = computed({
  get() {
    return get(value).linkedSetting;
  },
  set(newLinkedSetting: string | undefined) {
    input({
      value: get(value).value,
      ...(newLinkedSetting ? { linkedSetting: newLinkedSetting } : {})
    });
  }
});

const linkedPropertyValue = computed(() => {
  const property = get(value).linkedSetting;
  if (!property) {
    return null;
  }
  const item = get(linkableSettingOptions).find(
    item => item.identifier === property
  );

  if (!item) {
    return null;
  }

  return get(item.state);
});

const elemID = computed(() => `${get(identifier)}-switch`);
</script>

<template>
  <div class="flex gap-2 py-4">
    <VSwitch :id="elemID" v-model="value.value" :disabled="linkedModel" />
    <div class="w-full">
      <label :for="elemID" class="cursor-pointer">
        <div class="text-body-1 text-rui-text">
          {{ label }}
        </div>
        <div class="text-rui-text-secondary text-body-2">
          {{ hint }}
        </div>
      </label>
      <RuiCheckbox v-model="linkedModel" size="sm" color="primary" hide-details>
        <span class="text-caption">
          {{ t('accounting_settings.rule.overwrite_by_setting') }}
        </span>
      </RuiCheckbox>
      <div v-if="linkedModel" class="ml-7 mt-1 md:w-1/2">
        <VAutocomplete
          v-model="linkedSettingModel"
          outlined
          hide-details
          dense
          item-value="identifier"
          item-text="label"
          :items="linkableSettingOptions"
        />
        <div
          v-if="linkedPropertyValue !== null"
          class="flex items-center mt-2 gap-2"
        >
          {{ t('accounting_settings.rule.current_setting_value') }}
          <SuccessDisplay :success="linkedPropertyValue" />
        </div>
      </div>
    </div>
  </div>
</template>
