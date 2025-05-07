<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { abbreviationList } from '@/data/amount-formatter';
import { MINIMUM_DIGIT_TO_BE_ABBREVIATED } from '@/data/constraints';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const { t } = useI18n({ useScope: 'global' });

const abbreviate = ref<boolean>(false);
const minimumDigit = ref<string>(MINIMUM_DIGIT_TO_BE_ABBREVIATED.toString());
const { abbreviateNumber, minimumDigitToBeAbbreviated } = storeToRefs(useFrontendSettingsStore());

function resetMinimumDigitToBeAbbreviated() {
  set(minimumDigit, get(minimumDigitToBeAbbreviated).toString());
}

onMounted(() => {
  set(abbreviate, get(abbreviateNumber));
  resetMinimumDigitToBeAbbreviated();
});

const transform = (value?: string) => (value ? Number.parseInt(value) : value);

const textMap = [
  { label: t('amount_display.abbreviation.k'), symbol: 'k' },
  { label: t('amount_display.abbreviation.m'), symbol: 'M' },
  { label: t('amount_display.abbreviation.b'), symbol: 'B' },
  { label: t('amount_display.abbreviation.t'), symbol: 'T' },
];

const items = computed(() => textMap.map(({ label, symbol }) => {
  const digit = abbreviationList.find(item => item[1] === symbol)?.[0] || 0;
  const value = (digit + 1).toString();

  return {
    label: `${label} (${symbol})`,
    value,
  };
}));
</script>

<template>
  <div class="flex flex-col md:flex-col gap-8">
    <SettingsOption
      #default="{ error, success, update }"
      setting="abbreviateNumber"
      frontend-setting
    >
      <RuiSwitch
        v-model="abbreviate"
        data-cy="frontend-settings__fields__abbreviate_number"
        :label="t('frontend_settings.abbreviate_number.label')"
        :hint="t('frontend_settings.abbreviate_number.hint')"
        color="primary"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="update($event)"
      />
    </SettingsOption>
    <SettingsOption
      #default="{ error, success, updateImmediate }"
      :transform="transform"
      setting="minimumDigitToBeAbbreviated"
      frontend-setting
      @finished="resetMinimumDigitToBeAbbreviated()"
    >
      <RuiMenuSelect
        v-model="minimumDigit"
        :disabled="!abbreviate"
        :options="items"
        data-cy="frontend-settings__fields__minimum_digit_to_be_abbreviated"
        :label="t('frontend_settings.abbreviate_number.minimum_digit.label')"
        key-attr="value"
        text-attr="label"
        variant="outlined"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate($event)"
      />
    </SettingsOption>
  </div>
</template>
