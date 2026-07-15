<script setup lang="ts">
import { TimeFramePeriod, type TimeFrameSetting } from '@rotki/common';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import TimeFrameSettings from '@/modules/settings/general/TimeFrameSettings.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const defaultGraphTimeframe = ref<TimeFrameSetting>(TimeFramePeriod.ALL);
const visibleTimeframes = ref<TimeFramePeriod[]>([]);
const currentSessionTimeframe = ref<TimeFramePeriod>(TimeFramePeriod.ALL);

const { t } = useI18n({ useScope: 'global' });

const timeframe = useSetting('timeframe');
const { error: writeError, model: timeframeModel, success: writeSuccess } = useSettingModel('timeframeSetting');
const { model: visibleModel } = useSettingModel('visibleTimeframes');
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

function successMessage(timeframe: TimeFrameSetting): string {
  return t('frontend_settings.validation.timeframe.success', {
    timeframe,
  });
}

function resetTimeframeSetting(): void {
  set(defaultGraphTimeframe, get(timeframeModel));
}

function resetVisibleTimeframes(): void {
  set(visibleTimeframes, get(visibleModel));
}

function updateTimeframeSetting(value: TimeFrameSetting): void {
  set(timeframeModel, value);
}

function updateVisibleTimeframes(value: TimeFrameSetting[]): void {
  set(visibleModel, value);
}

watch(timeframeModel, () => {
  clearAll();
  resetTimeframeSetting();
});

watch(visibleModel, () => {
  resetVisibleTimeframes();
});

watch(writeSuccess, (saved) => {
  if (saved)
    setSuccess(successMessage(get(timeframeModel)), true);
});

watch(writeError, (message) => {
  if (message)
    setError(`${t('frontend_settings.validation.timeframe.error')}: ${message}`, true);
});

onMounted(() => {
  set(currentSessionTimeframe, get(timeframe));
  resetTimeframeSetting();
  resetVisibleTimeframes();
});
</script>

<template>
  <SettingsItem setting-key="timeframeSetting">
    <template #title>
      {{ t('timeframe_settings.default_timeframe') }}
    </template>
    <template #subtitle>
      {{ t('timeframe_settings.default_timeframe_description') }}
    </template>
    <TimeFrameSettings
      :message="{ error, success }"
      :value="defaultGraphTimeframe"
      :visible-timeframes="visibleTimeframes"
      :current-session-timeframe="currentSessionTimeframe"
      @timeframe-change="updateTimeframeSetting($event)"
      @visible-timeframes-change="updateVisibleTimeframes($event)"
    />
  </SettingsItem>
</template>
