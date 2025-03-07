<script setup lang="ts">
import type { AccountingRuleWithLinkedProperty } from '@/types/settings/accounting';
import SuccessDisplay from '@/components/display/SuccessDisplay.vue';
import { useAccountingRuleMappings } from '@/composables/settings/accounting/rule-mapping';
import { useSimplePropVModel } from '@/utils/model';

const props = defineProps<{
  identifier: string;
  modelValue: AccountingRuleWithLinkedProperty;
  label: string;
  hint: string;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: AccountingRuleWithLinkedProperty): void;
}>();

const { identifier } = toRefs(props);
const { t } = useI18n();

const value = useSimplePropVModel(props, 'value', emit);

function updateModelValue(newValue: AccountingRuleWithLinkedProperty) {
  emit('update:model-value', newValue);
}

const { accountingRuleLinkedMappingData } = useAccountingRuleMappings();

const linkableSettingOptions = accountingRuleLinkedMappingData(identifier);

const linkedModel = computed({
  get() {
    return !!props.modelValue.linkedSetting;
  },
  set(newValue: boolean) {
    if (newValue) {
      updateModelValue({
        linkedSetting: get(linkableSettingOptions)[0]?.identifier || '',
        value: props.modelValue.value,
      });
    }
    else {
      updateModelValue({
        value: props.modelValue.value,
      });
    }
  },
});

const linkedSettingModel = computed({
  get() {
    return props.modelValue.linkedSetting;
  },
  set(newLinkedSetting: string | undefined) {
    updateModelValue({
      value: props.modelValue.value,
      ...(newLinkedSetting ? { linkedSetting: newLinkedSetting } : {}),
    });
  },
});

const linkedPropertyValue = computed(() => {
  const property = props.modelValue.linkedSetting;
  if (!property)
    return null;

  const item = get(linkableSettingOptions).find(item => item.identifier === property);

  if (!item)
    return null;

  return get(item.state);
});

const elemID = computed(() => `${get(identifier)}-switch`);
</script>

<template>
  <div class="flex gap-4 py-4">
    <RuiSwitch
      :id="elemID"
      v-model="value"
      color="primary"
      :disabled="linkedModel"
    />
    <div class="w-full">
      <label
        :for="elemID"
        class="cursor-pointer"
      >
        <div class="text-body-1 text-rui-text">
          {{ label }}
        </div>
        <div class="text-rui-text-secondary text-body-2">
          {{ hint }}
        </div>
      </label>
      <RuiCheckbox
        v-model="linkedModel"
        size="sm"
        color="primary"
        hide-details
      >
        <span class="text-caption">
          {{ t('accounting_settings.rule.overwrite_by_setting') }}
        </span>
      </RuiCheckbox>
      <div
        v-if="linkedModel"
        class="ml-7 mt-1 md:w-1/2"
      >
        <RuiMenuSelect
          v-model="linkedSettingModel"
          variant="outlined"
          hide-details
          dense
          key-attr="identifier"
          text-attr="label"
          :options="linkableSettingOptions"
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
