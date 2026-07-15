<script setup lang="ts">
import { Defaults } from '@/modules/core/common/defaults';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingResetConfirmButton from '@/modules/settings/SettingResetConfirmButton.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const { compact = false } = defineProps<{
  compact?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const SECONDS_PER_MINUTE = 60;

const { error: batchWriteError, flush: flushBatch, model: batchModel, success: batchWriteSuccess } = useSettingModel('internalTxsToRepull', { debounce: 1500 });
const { error: frequencyWriteError, flush: flushFrequency, model: frequencyModel, success: frequencyWriteSuccess } = useSettingModel('internalTxConflictRepullFrequency', { debounce: 1500 });
const { clearAll: clearBatchMessages, error: batchError, setError: setBatchError, setSuccess: setBatchSuccess, success: batchSuccess } = useClearableMessages();
const { clearAll: clearFrequencyMessages, error: frequencyError, setError: setFrequencyError, setSuccess: setFrequencySuccess, success: frequencySuccess } = useClearableMessages();

const batchSize = ref<string>(get(batchModel).toString());
const frequency = ref<string>((get(frequencyModel) / SECONDS_PER_MINUTE).toString());

function updateBatchSize(value: string): void {
  clearBatchMessages();
  if (value)
    set(batchModel, Number.parseInt(value));
}

function updateFrequency(value: string): void {
  clearFrequencyMessages();
  if (value)
    set(frequencyModel, Number.parseFloat(value) * SECONDS_PER_MINUTE);
}

async function resetBatchSize(): Promise<void> {
  clearBatchMessages();
  set(batchModel, Defaults.DEFAULT_INTERNAL_TXS_TO_REPULL);
  await flushBatch();
}

async function resetFrequency(): Promise<void> {
  clearFrequencyMessages();
  set(frequencyModel, Defaults.DEFAULT_INTERNAL_TX_CONFLICT_REPULL_FREQUENCY);
  await flushFrequency();
}

watch(batchModel, (value) => {
  set(batchSize, value.toString());
});

watch(frequencyModel, (value) => {
  set(frequency, (value / SECONDS_PER_MINUTE).toString());
});

watch(batchWriteSuccess, (saved) => {
  if (saved)
    setBatchSuccess('', true);
});

watch(batchWriteError, (message) => {
  if (message)
    setBatchError(`${t('general_settings.history_event.internal_tx_conflicts.batch_size.error')}: ${message}`, true);
});

watch(frequencyWriteSuccess, (saved) => {
  if (saved)
    setFrequencySuccess('', true);
});

watch(frequencyWriteError, (message) => {
  if (message)
    setFrequencyError(`${t('general_settings.history_event.internal_tx_conflicts.frequency.error')}: ${message}`, true);
});
</script>

<template>
  <div :class="compact ? 'flex flex-col gap-3 pt-4' : undefined">
    <SettingsItem setting-key="internalTxsToRepull">
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
      <div class="flex items-start w-full">
        <RuiTextField
          v-model="batchSize"
          variant="outlined"
          color="primary"
          class="w-full"
          :dense="compact"
          :label="t('general_settings.history_event.internal_tx_conflicts.batch_size.label')"
          type="number"
          :min="1"
          :success-messages="batchSuccess"
          :error-messages="batchError"
          @update:model-value="updateBatchSize($event)"
        />
        <SettingResetConfirmButton
          :compact="compact"
          @confirm="resetBatchSize()"
        />
      </div>
    </SettingsItem>
    <SettingsItem>
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
      <div class="flex items-start w-full">
        <RuiTextField
          v-model="frequency"
          variant="outlined"
          color="primary"
          class="w-full"
          :dense="compact"
          :label="t('general_settings.history_event.internal_tx_conflicts.frequency.label')"
          type="number"
          :min="0.5"
          :step="0.5"
          :success-messages="frequencySuccess"
          :error-messages="frequencyError"
          @update:model-value="updateFrequency($event)"
        />
        <SettingResetConfirmButton
          :compact="compact"
          @confirm="resetFrequency()"
        />
      </div>
    </SettingsItem>
  </div>
</template>
