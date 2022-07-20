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

    <div class="mt-12">
      <div class="text-h6">
        {{ $t('frontend_settings.subtitle.refresh') }}
      </div>

      <v-row class="mt-1">
        <v-col class="grow">
          <settings-option
            #default="{ error, success, update }"
            setting="refreshPeriod"
            frontend-setting
            :transform="value => (value ? parseInt(value) : value)"
            :rules="refreshPeriodRules"
            :error-message="
              $tc('frontend_settings.validation.refresh_period.error')
            "
            @finished="resetRefreshPeriod"
          >
            <v-text-field
              v-model="refreshPeriod"
              outlined
              :disabled="!refreshEnabled"
              type="number"
              :min="minRefreshPeriod"
              :max="maxRefreshPeriod"
              :label="$t('frontend_settings.label.refresh')"
              persistent-hint
              :rules="refreshPeriodRules"
              :hint="$t('frontend_settings.hint.refresh')"
              :success-messages="success"
              :error-messages="error"
              @change="update"
            />
          </settings-option>
        </v-col>
        <v-col class="shrink">
          <settings-option
            #default="{ update }"
            setting="refreshPeriod"
            frontend-setting
            :transform="value => (value ? 30 : -1)"
            :error-message="
              $tc('frontend_settings.validation.refresh_period.error')
            "
            @finished="resetRefreshPeriod"
          >
            <v-switch
              v-model="refreshEnabled"
              class="mt-3"
              :label="$t('frontend_settings.label.refresh_enabled')"
              @change="update"
            />
          </settings-option>
        </v-col>
      </v-row>
    </div>

    <div class="mt-8">
      <div class="text-h6">
        {{ $t('frontend_settings.subtitle.query') }}
      </div>

      <settings-option
        #default="{ error, success, update }"
        class="mt-1"
        setting="queryPeriod"
        frontend-setting
        :transform="value => (value ? parseInt(value) : value)"
        :error-message="
          $tc('frontend_settings.validation.periodic_query.error')
        "
        :rules="queryPeriodRules"
        @updated="restartMonitor"
        @finished="resetQueryPeriod"
      >
        <v-text-field
          v-model="queryPeriod"
          outlined
          class="general-settings__fields__periodic-client-query-period"
          :label="$t('frontend_settings.label.query_period')"
          :hint="$t('frontend_settings.label.query_period_hint')"
          type="number"
          :rules="queryPeriodRules"
          :min="minQueryPeriod"
          :max="maxQueryPeriod"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>
    </div>

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
import { computed, onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import ThemeManagerLock from '@/components/premium/ThemeManagerLock.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import Explorers from '@/components/settings/explorers/Explorers.vue';
import TimeFrameSettings from '@/components/settings/general/TimeFrameSettings.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { getPremium, getSessionState } from '@/composables/session';
import { useSettings } from '@/composables/settings';
import { setupGeneralStatistics } from '@/composables/statistics';
import { Constraints } from '@/data/constraints';
import i18n from '@/i18n';
import { ThemeManager } from '@/premium/premium';
import { monitor } from '@/services/monitoring';

const queryPeriod = ref<string>('5');
const scrambleData = ref<boolean>(false);
const defaultGraphTimeframe = ref<TimeFrameSetting>(TimeFramePeriod.ALL);
const visibleTimeframes = ref<TimeFrameSetting[]>([]);
const currentSessionTimeframe = ref<TimeFramePeriod>(TimeFramePeriod.ALL);
const refreshPeriod = ref<string>('');
const refreshEnabled = ref<boolean>(false);
const zeroBased = ref<boolean>(false);
const showGraphRangeSelector = ref<boolean>(true);
const includeNfts = ref<boolean>(true);
const animationsEnabled = ref<boolean>(true);
const enableEthNames = ref<boolean>(true);

const premium = getPremium();

const { fetchNetValue } = setupGeneralStatistics();

const minQueryPeriod = 5;
const maxQueryPeriod = 3600;

const queryPeriodRules = [
  (v: string) =>
    !!v ||
    i18n.t('frontend_settings.validation.periodic_query.non_empty').toString(),
  (v: string) =>
    (v && parseInt(v) >= minQueryPeriod && parseInt(v) < maxQueryPeriod) ||
    i18n
      .t('frontend_settings.validation.periodic_query.invalid_period', {
        start: minQueryPeriod,
        end: maxQueryPeriod
      })
      .toString()
];

const minRefreshPeriod = 30;
const maxRefreshPeriod = Constraints.MAX_MINUTES_DELAY;
const refreshPeriodRules = computed<((v: string) => boolean | string)[]>(() => {
  return [
    (v: string) =>
      !!v ||
      !get(refreshEnabled) ||
      i18n
        .t('frontend_settings.validation.refresh_period.non_empty')
        .toString(),
    (v: string) =>
      (v &&
        parseInt(v) >= minRefreshPeriod &&
        parseInt(v) < maxRefreshPeriod) ||
      !get(refreshEnabled) ||
      i18n
        .t('frontend_settings.validation.refresh_period.invalid_period', {
          start: minRefreshPeriod,
          end: maxRefreshPeriod
        })
        .toString()
  ];
});

const { frontendSettings } = useSettings();

const resetTimeframeSetting = () => {
  const frontendSettingsVal = get(frontendSettings);
  set(defaultGraphTimeframe, frontendSettingsVal.timeframeSetting);
};

const resetVisibleTimeframes = () => {
  const frontendSettingsVal = get(frontendSettings);
  set(visibleTimeframes, frontendSettingsVal.visibleTimeframes);
};

const resetRefreshPeriod = () => {
  const frontendSettingsVal = get(frontendSettings);
  const period = frontendSettingsVal.refreshPeriod;
  set(refreshEnabled, period > 0);
  set(refreshPeriod, get(refreshEnabled) ? period.toString() : '');
};

const resetQueryPeriod = () => {
  const frontendSettingsVal = get(frontendSettings);
  set(queryPeriod, frontendSettingsVal.queryPeriod.toString());
};

const restartMonitor = () => {
  monitor.restart();
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
  resetRefreshPeriod();
  resetQueryPeriod();
});
</script>
