<template>
  <setting-category>
    <template #title>
      {{ $t('frontend_settings.title') }}
    </template>

    <settings-option
      #default="{ error, success, update }"
      setting="animationsEnabled"
      session-setting
      :transform="value => !value"
      :error-message="$tc('frontend_settings.validation.animations.error')"
    >
      <v-switch
        :value="!animationsEnabled"
        class="general-settings__fields__animation-enabled mt-0"
        :label="$t('frontend_settings.label.animations')"
        :success-messages="success"
        :error-messages="error"
        @change="update"
      />
    </settings-option>

    <settings-option
      #default="{ error, success, update }"
      setting="scrambleData"
      session-setting
      :error-message="$tc('frontend_settings.validation.scramble.error')"
    >
      <v-switch
        v-model="scrambleData"
        class="general-settings__fields__scramble-data"
        :label="$t('frontend_settings.label.scramble')"
        :success-messages="success"
        :error-messages="error"
        @change="update"
      />
    </settings-option>

    <div class="mt-8">
      <div class="d-flex align-center">
        <div class="text-h6">
          {{ $t('frontend_settings.subtitle.eth_names') }}
        </div>
        <div class="pl-2">
          <eth-names-hint />
        </div>
      </div>

      <settings-option
        #default="{ error, success, update }"
        setting="enableEthNames"
        frontend-setting
        :error-message="
          $tc('frontend_settings.validation.enable_eth_names.error')
        "
      >
        <v-switch
          v-model="enableEthNames"
          class="general-settings__fields__enable_eth_names mb-4 mt-2"
          :label="$t('frontend_settings.label.enable_eth_names')"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>
    </div>

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

    <div class="mt-8">
      <div class="text-h6">
        {{ $t('frontend_settings.subtitle.graph_basis') }}
      </div>

      <settings-option
        #default="{ error, success, update }"
        setting="graphZeroBased"
        frontend-setting
      >
        <v-switch
          v-model="zeroBased"
          class="general-settings__fields__zero-base mb-4 mt-2"
          :label="$t('frontend_settings.label.zero_based')"
          :hint="$t('frontend_settings.label.zero_based_hint')"
          persistent-hint
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>
    </div>

    <div class="mt-8">
      <div class="text-h6">
        {{ $t('frontend_settings.subtitle.show_graph_range_selector') }}
      </div>

      <settings-option
        #default="{ error, success, update }"
        setting="showGraphRangeSelector"
        frontend-setting
      >
        <v-switch
          v-model="showGraphRangeSelector"
          class="general-settings__fields__zero-base mb-4 mt-2"
          :label="$t('frontend_settings.label.show_graph_range_selector')"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>
    </div>

    <div class="mt-4">
      <div class="text-h6">
        {{ $t('frontend_settings.subtitle.include_nfts') }}
      </div>

      <settings-option
        #default="{ error, success, update }"
        setting="nftsInNetValue"
        frontend-setting
        @finished="fetchNetValue"
      >
        <v-switch
          v-model="includeNfts"
          class="general-settings__fields__zero-base mb-4 mt-2"
          :label="$t('frontend_settings.label.include_nfts')"
          :hint="$t('frontend_settings.label.include_nfts_hint')"
          persistent-hint
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>
    </div>

    <refresh-setting />
    <query-period-setting />
    <explorers />
    <theme-manager v-if="premium" class="mt-12" />
    <theme-manager-lock v-else class="mt-12" />
  </setting-category>
</template>

<script setup lang="ts">
import {
  TimeFramePeriod,
  TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import ThemeManagerLock from '@/components/premium/ThemeManagerLock.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import Explorers from '@/components/settings/explorers/Explorers.vue';
import QueryPeriodSetting from '@/components/settings/general/QueryPeriodSetting.vue';
import RefreshSetting from '@/components/settings/general/RefreshSetting.vue';
import TimeFrameSettings from '@/components/settings/general/TimeFrameSettings.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { getPremium, getSessionState } from '@/composables/session';
import { useSettings } from '@/composables/settings';
import { setupGeneralStatistics } from '@/composables/statistics';
import { ThemeManager } from '@/premium/premium';

const scrambleData = ref<boolean>(false);
const defaultGraphTimeframe = ref<TimeFrameSetting>(TimeFramePeriod.ALL);
const visibleTimeframes = ref<TimeFrameSetting[]>([]);
const currentSessionTimeframe = ref<TimeFramePeriod>(TimeFramePeriod.ALL);
const zeroBased = ref<boolean>(false);
const showGraphRangeSelector = ref<boolean>(true);
const includeNfts = ref<boolean>(true);
const animationsEnabled = ref<boolean>(true);
const enableEthNames = ref<boolean>(true);

const premium = getPremium();

const { fetchNetValue } = setupGeneralStatistics();

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
  set(scrambleData, state.scrambleData);
  set(animationsEnabled, state.animationsEnabled);
  set(currentSessionTimeframe, state.timeframe);

  const frontendSettingsVal = get(frontendSettings);
  set(zeroBased, frontendSettingsVal.graphZeroBased);
  set(showGraphRangeSelector, frontendSettingsVal.showGraphRangeSelector);
  set(includeNfts, frontendSettingsVal.nftsInNetValue);
  set(enableEthNames, frontendSettingsVal.enableEthNames);
  resetTimeframeSetting();
  resetVisibleTimeframes();
});
</script>
