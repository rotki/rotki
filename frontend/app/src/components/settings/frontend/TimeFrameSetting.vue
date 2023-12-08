<script setup lang="ts">
import {
  TimeFramePeriod,
  type TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';

const defaultGraphTimeframe = ref<TimeFrameSetting>(TimeFramePeriod.ALL);
const visibleTimeframes = ref<TimeFramePeriod[]>([]);
const currentSessionTimeframe = ref<TimeFramePeriod>(TimeFramePeriod.ALL);

const { t } = useI18n();

const { timeframe } = useSessionSettingsStore();
const { timeframeSetting, visibleTimeframes: visible } = storeToRefs(
  useFrontendSettingsStore()
);

const resetTimeframeSetting = () => {
  set(defaultGraphTimeframe, get(timeframeSetting));
};

const resetVisibleTimeframes = () => {
  set(visibleTimeframes, get(visible));
};

const successMessage = (timeframe: TimeFramePeriod) =>
  t('frontend_settings.validation.timeframe.success', {
    timeframe
  });

onMounted(() => {
  set(currentSessionTimeframe, get(timeframe));
  resetTimeframeSetting();
  resetVisibleTimeframes();
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, update: updateTimeframeSetting }"
    setting="timeframeSetting"
    frontend-setting
    :success-message="successMessage"
    :error-message="t('frontend_settings.validation.timeframe.error')"
    @finished="resetTimeframeSetting()"
  >
    <SettingsOption
      #default="{ update: updateVisibleTimeframes }"
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
</template>
