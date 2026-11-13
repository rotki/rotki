<script setup lang="ts">
import { Defaults } from '@/modules/core/common/defaults';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';
import { useSetting } from '@/modules/settings/use-setting';

const { t } = useI18n({ useScope: 'global' });

const enabled = useSetting('deemphasizeSmallValueEvents');
const currencySymbol = useSetting('currencySymbol');

/** The threshold is a fiat amount, so unlike the other numeric settings it keeps its decimals. */
function toThreshold(value: string): number {
  return Number.parseFloat(value);
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <SettingSwitch
      setting="deemphasizeSmallValueEvents"
      data-testid="small-value-events-toggle"
      :label="t('general_settings.history_event.small_value_events.label')"
      :error-message="t('general_settings.history_event.small_value_events.validation.error')"
    />
    <SettingNumber
      setting="smallValueEventThreshold"
      data-testid="small-value-events-threshold"
      :label="t('general_settings.history_event.small_value_events.threshold.label', { symbol: currencySymbol })"
      :hint="t('general_settings.history_event.small_value_events.threshold.hint')"
      :disabled="!enabled"
      :min="0"
      :default="Defaults.DEFAULT_SMALL_VALUE_EVENT_THRESHOLD"
      :transform="toThreshold"
      step="0.01"
      :error-message="t('general_settings.history_event.small_value_events.threshold.validation.error')"
      :success-message="t('general_settings.history_event.small_value_events.threshold.validation.success')"
    />
  </div>
</template>
