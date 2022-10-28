<template>
  <settings-option
    #default="{ error, success, update: updateTimeframeSetting }"
    class="mt-4"
    setting="timeframeSetting"
    frontend-setting
    :success-message="successMessage"
    :error-message="tc('frontend_settings.validation.timeframe.error')"
    @finished="resetTimeframeSetting"
  >
    <settings-option
      #default="{ update: updateVisibleTimeframes }"
      setting="visibleTimeframes"
      frontend-setting
      @finished="resetVisibleTimeframes"
    >
      <time-frame-settings
        :message="{ error, success }"
        :value="defaultGraphTimeframe"
        :visible-timeframes="visibleTimeframes"
        :current-session-timeframe="currentSessionTimeframe"
        @timeframe-change="updateTimeframeSetting"
        @visible-timeframes-change="updateVisibleTimeframes"
      />
    </settings-option>
  </settings-option>
</template>

<script setup lang="ts">
import {
  TimeFramePeriod,
  TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useSessionSettingsStore } from '@/store/settings/session';

const defaultGraphTimeframe = ref<TimeFrameSetting>(TimeFramePeriod.ALL);
const visibleTimeframes = ref<TimeFrameSetting[]>([]);
const currentSessionTimeframe = ref<TimeFramePeriod>(TimeFramePeriod.ALL);

const { tc } = useI18n();

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
  tc('frontend_settings.validation.timeframe.success', 0, {
    timeframe
  });

onMounted(() => {
  set(currentSessionTimeframe, get(timeframe));
  resetTimeframeSetting();
  resetVisibleTimeframes();
});
</script>
