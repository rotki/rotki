<script setup lang="ts">
import { TimeFramePeriod, type TimeFrameSetting } from '@rotki/common';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import TimeFrameSettings from '@/components/settings/general/TimeFrameSettings.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useSessionSettingsStore } from '@/store/settings/session';

const defaultGraphTimeframe = ref<TimeFrameSetting>(TimeFramePeriod.ALL);
const visibleTimeframes = ref<TimeFramePeriod[]>([]);
const currentSessionTimeframe = ref<TimeFramePeriod>(TimeFramePeriod.ALL);

const { t } = useI18n({ useScope: 'global' });

const { timeframe } = useSessionSettingsStore();
const { timeframeSetting, visibleTimeframes: visible } = storeToRefs(useFrontendSettingsStore());

function resetTimeframeSetting() {
  set(defaultGraphTimeframe, get(timeframeSetting));
}

function resetVisibleTimeframes() {
  set(visibleTimeframes, get(visible));
}

function successMessage(timeframe: TimeFramePeriod) {
  return t('frontend_settings.validation.timeframe.success', {
    timeframe,
  });
}

onMounted(() => {
  set(currentSessionTimeframe, get(timeframe));
  resetTimeframeSetting();
  resetVisibleTimeframes();
});
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('timeframe_settings.default_timeframe') }}
    </template>
    <template #subtitle>
      {{ t('timeframe_settings.default_timeframe_description') }}
    </template>
    <SettingsOption
      #default="{ error, success, updateImmediate: updateTimeframeSetting }"
      setting="timeframeSetting"
      frontend-setting
      :success-message="successMessage"
      :error-message="t('frontend_settings.validation.timeframe.error')"
      @finished="resetTimeframeSetting()"
    >
      <SettingsOption
        #default="{ updateImmediate: updateVisibleTimeframes }"
        setting="visibleTimeframes"
        frontend-setting
        @finished="resetVisibleTimeframes()"
      >
        <TimeFrameSettings
          :message="{ error, success }"
          :value="defaultGraphTimeframe"
          :visible-timeframes="visibleTimeframes"
          :current-session-timeframe="currentSessionTimeframe"
          @timeframe-change="updateTimeframeSetting($event)"
          @visible-timeframes-change="updateVisibleTimeframes($event)"
        />
      </SettingsOption>
    </SettingsOption>
  </SettingsItem>
</template>
