<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { Defaults } from '@/modules/common/defaults';
import SettingResetConfirmButton from '@/modules/settings/SettingResetConfirmButton.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const { compact = false } = defineProps<{
  compact?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const store = useGeneralSettingsStore();
const { internalTxConflictRepullFrequency: storedFrequency, internalTxsToRepull: storedBatchSize } = storeToRefs(store);

const batchSize = ref<string>(Defaults.DEFAULT_INTERNAL_TXS_TO_REPULL.toString());
const SECONDS_PER_MINUTE = 60;
const frequency = ref<string>((Defaults.DEFAULT_INTERNAL_TX_CONFLICT_REPULL_FREQUENCY / SECONDS_PER_MINUTE).toString());

function resetBatchSize(update: (value: number) => void): void {
  const defaultVal = Defaults.DEFAULT_INTERNAL_TXS_TO_REPULL;
  update(defaultVal);
  set(batchSize, defaultVal.toString());
}

function resetFrequency(update: (value: number) => void): void {
  const defaultVal = Defaults.DEFAULT_INTERNAL_TX_CONFLICT_REPULL_FREQUENCY;
  update(defaultVal);
  set(frequency, (defaultVal / SECONDS_PER_MINUTE).toString());
}

onMounted(() => {
  set(batchSize, get(storedBatchSize).toString());
  set(frequency, (get(storedFrequency) / SECONDS_PER_MINUTE).toString());
});
</script>

<template>
  <div :class="compact ? 'flex flex-col gap-3 pt-4' : undefined">
    <SettingsOption
      setting="internalTxsToRepull"
      :error-message="t('general_settings.history_event.internal_tx_conflicts.batch_size.error')"
    >
      <template
        v-if="!compact"
        #title
      >
        {{ t('general_settings.history_event.internal_tx_conflicts.batch_size.title') }}
      </template>
      <template
        v-if="!compact"
        #subtitle
      >
        {{ t('general_settings.history_event.internal_tx_conflicts.batch_size.subtitle') }}
      </template>
      <template #default="{ error, success, update, updateImmediate }">
        <div class="flex items-start w-full">
          <RuiTextField
            v-model.number="batchSize"
            variant="outlined"
            color="primary"
            class="w-full"
            :dense="compact"
            :label="t('general_settings.history_event.internal_tx_conflicts.batch_size.label')"
            type="number"
            :min="1"
            :success-messages="success"
            :error-messages="error"
            @update:model-value="update($event ? parseInt($event) : $event)"
          />
          <SettingResetConfirmButton
            :compact="compact"
            @confirm="resetBatchSize(updateImmediate)"
          />
        </div>
      </template>
    </SettingsOption>
    <SettingsOption
      setting="internalTxConflictRepullFrequency"
      :error-message="t('general_settings.history_event.internal_tx_conflicts.frequency.error')"
    >
      <template
        v-if="!compact"
        #title
      >
        {{ t('general_settings.history_event.internal_tx_conflicts.frequency.title') }}
      </template>
      <template
        v-if="!compact"
        #subtitle
      >
        {{ t('general_settings.history_event.internal_tx_conflicts.frequency.subtitle') }}
      </template>
      <template #default="{ error, success, update, updateImmediate }">
        <div class="flex items-start w-full">
          <RuiTextField
            v-model.number="frequency"
            variant="outlined"
            color="primary"
            class="w-full"
            :dense="compact"
            :label="t('general_settings.history_event.internal_tx_conflicts.frequency.label')"
            type="number"
            :min="0.5"
            :step="0.5"
            :success-messages="success"
            :error-messages="error"
            @update:model-value="update($event ? Number.parseFloat($event) * SECONDS_PER_MINUTE : $event)"
          />
          <SettingResetConfirmButton
            :compact="compact"
            @confirm="resetFrequency(updateImmediate)"
          />
        </div>
      </template>
    </SettingsOption>
  </div>
</template>
