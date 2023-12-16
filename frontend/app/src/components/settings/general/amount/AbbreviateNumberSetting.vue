<script setup lang="ts">
import { MINIMUM_DIGIT_TO_BE_ABBREVIATED } from '@/data/constraints';
import { abbreviationList } from '@/data/amount-formatter';

const { t } = useI18n();

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

const items = computed(() => {
  const textMap = {
    k: t('amount_display.abbreviation.k'),
    M: t('amount_display.abbreviation.m'),
    B: t('amount_display.abbreviation.b'),
    T: t('amount_display.abbreviation.t'),
  };

  return Object.entries(textMap).map(([abbreviation, label]) => {
    const digit = abbreviationList.find(item => item[1] === abbreviation)?.[0] || 0;
    const value = (digit + 1).toString();

    return {
      value,
      label: `${label} (${abbreviation})`,
    };
  });
});
</script>

<template>
  <div class="flex flex-col md:flex-row gap-8 mt-4">
    <SettingsOption
      #default="{ error, success, update }"
      setting="abbreviateNumber"
      class="w-[26rem]"
      frontend-setting
    >
      <RuiSwitch
        v-model="abbreviate"
        data-cy="frontend-settings__fields__abbreviate_number"
        :label="t('frontend_settings.label.abbreviate_number')"
        :hint="t('frontend_settings.subtitle.abbreviate_number')"
        color="primary"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="update($event)"
      />
    </SettingsOption>
    <SettingsOption
      #default="{ error, success, updateImmediate }"
      :transform="transform"
      class="md:min-w-[18rem]"
      setting="minimumDigitToBeAbbreviated"
      frontend-setting
      @finished="resetMinimumDigitToBeAbbreviated()"
    >
      <RuiMenuSelect
        v-model="minimumDigit"
        :disabled="!abbreviate"
        :options="items"
        data-cy="frontend-settings__fields__minimum_digit_to_be_abbreviated"
        :label="t('frontend_settings.label.minimum_digit_to_be_abbreviated')"
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
