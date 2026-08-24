<script setup lang="ts">
import { abbreviationList } from '@/modules/assets/amount-display/amount-formatter';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const { t } = useI18n({ useScope: 'global' });

const abbreviateNumber = useSetting('abbreviateNumber');
const { error: writeError, model, success: writeSuccess } = useSettingModel('minimumDigitToBeAbbreviated');
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

// The setting stores a number; the select binds strings, so map both ways.
const minimumDigit = computed<string>({
  get: () => get(model).toString(),
  set: (value) => {
    set(model, Number.parseInt(value));
  },
});

const textMap = [
  { label: t('amount_display.abbreviation.k'), symbol: 'k' },
  { label: t('amount_display.abbreviation.m'), symbol: 'M' },
  { label: t('amount_display.abbreviation.b'), symbol: 'B' },
  { label: t('amount_display.abbreviation.t'), symbol: 'T' },
];

const items = computed<{ label: string; value: string }[]>(() => textMap.map(({ label, symbol }) => {
  const digit = abbreviationList.find(item => item[1] === symbol)?.[0] || 0;
  const value = (digit + 1).toString();

  return {
    label: `${label} (${symbol})`,
    value,
  };
}));

watch(model, () => {
  clearAll();
});

watch(writeSuccess, (saved) => {
  if (saved)
    setSuccess('', true);
});

watch(writeError, (message) => {
  if (message)
    setError(message, true);
});
</script>

<template>
  <div class="flex flex-col md:flex-col gap-8">
    <SettingSwitch
      setting="abbreviateNumber"
      data-testid="frontend-settings-abbreviate-number"
      :label="t('frontend_settings.abbreviate_number.label')"
      :hint="t('frontend_settings.abbreviate_number.hint')"
    />
    <RuiMenuSelect
      v-model="minimumDigit"
      :disabled="!abbreviateNumber"
      :options="items"
      data-testid="frontend-settings-minimum-digit-to-be-abbreviated"
      :label="t('frontend_settings.abbreviate_number.minimum_digit.label')"
      key-attr="value"
      text-attr="label"
      variant="outlined"
      :success-messages="success"
      :error-messages="error"
    />
  </div>
</template>
