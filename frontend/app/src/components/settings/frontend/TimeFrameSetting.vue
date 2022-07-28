<template>
  <settings-option
    #default="{ error, success, update: updateTimeframeSetting }"
    class="mt-4"
    setting="timeframeSetting"
    frontend-setting
    :success-message="
      timeframe =>
        $tc('frontend_settings.validation.timeframe.success', 0, {
          timeframe
        })
    "
    :error-message="$tc('frontend_settings.validation.timeframe.error')"
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
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { getSessionState } from '@/composables/session';
import { useSettings } from '@/composables/settings';

const defaultGraphTimeframe = ref<TimeFrameSetting>(TimeFramePeriod.ALL);
const visibleTimeframes = ref<TimeFrameSetting[]>([]);
const currentSessionTimeframe = ref<TimeFramePeriod>(TimeFramePeriod.ALL);

const { frontendSettings } = useSettings();

const resetTimeframeSetting = () => {
  const frontendSettingsVal = get(frontendSettings);
  set(defaultGraphTimeframe, frontendSettingsVal.timeframeSetting);
};

const resetVisibleTimeframes = () => {
  const frontendSettingsVal = get(frontendSettings);
  set(visibleTimeframes, frontendSettingsVal.visibleTimeframes);
};

onMounted(() => {
  const state = getSessionState();
  set(currentSessionTimeframe, state.timeframe);
  resetTimeframeSetting();
  resetVisibleTimeframes();
});
</script>
