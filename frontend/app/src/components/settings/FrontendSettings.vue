<template>
  <setting-category>
    <template #title>
      {{ $t('frontend_settings.title') }}
    </template>
    <v-switch
      v-model="scrambleData"
      class="general-settings__fields__scramble-data"
      :label="$t('frontend_settings.label.scramble')"
      :success-messages="settingsMessages[SCRAMBLE_DATA].success"
      :error-messages="settingsMessages[SCRAMBLE_DATA].error"
      @change="onScrambleDataChange($event)"
    />
    <time-frame-settings
      :message="settingsMessages[TIMEFRAME]"
      :value="defaultGraphTimeframe"
      @timeframe-change="onTimeframeChange"
    />
    <v-text-field
      v-model="queryPeriod"
      class="general-settings__fields__periodic-client-query-period"
      :label="$t('frontend_settings.label.query_period')"
      :hint="$t('frontend_settings.label.query_period_hint')"
      type="number"
      min="5"
      max="3600"
      :success-messages="settingsMessages[QUERY_PERIOD].success"
      :error-messages="settingsMessages[QUERY_PERIOD].error"
      @change="onQueryPeriodChange($event)"
    />
  </setting-category>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import TimeFrameSettings from '@/components/settings/general/TimeFrameSettings.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import {
  BaseMessage,
  makeMessage,
  settingsMessages
} from '@/components/settings/utils';
import SettingsMixin from '@/mixins/settings-mixin';
import { monitor } from '@/services/monitoring';
import {
  QUERY_PERIOD,
  TIMEFRAME_ALL,
  TIMEFRAME_SETTING
} from '@/store/settings/consts';
import {
  FrontendSettingsPayload,
  TimeFrameSetting
} from '@/store/settings/types';

const SETTING_SCRAMBLE_DATA = 'scrambleData';
const SETTING_TIMEFRAME = 'timeframe';
const SETTING_QUERY_PERIOD = 'queryPeriod';

const SETTINGS = [
  SETTING_SCRAMBLE_DATA,
  SETTING_TIMEFRAME,
  SETTING_QUERY_PERIOD
] as const;

type SettingsEntries = typeof SETTINGS[number];

@Component({
  components: { TimeFrameSettings, SettingCategory }
})
export default class FrontendSettings extends Mixins<
  SettingsMixin<SettingsEntries>
>(SettingsMixin) {
  queryPeriod: string = '5';
  scrambleData: boolean = false;
  defaultGraphTimeframe: TimeFrameSetting = TIMEFRAME_ALL;

  readonly SCRAMBLE_DATA = SETTING_SCRAMBLE_DATA;
  readonly TIMEFRAME = SETTING_TIMEFRAME;
  readonly QUERY_PERIOD = SETTING_QUERY_PERIOD;

  async onTimeframeChange(timeframe: TimeFrameSetting) {
    const payload: FrontendSettingsPayload = {
      [TIMEFRAME_SETTING]: timeframe
    };

    const messages: BaseMessage = {
      success: this.$t('frontend_settings.validation.timeframe.success', {
        timeframe: timeframe
      }).toString(),
      error: this.$t('frontend_settings.validation.timeframe.error').toString()
    };

    const { success } = await this.modifyFrontendSetting(
      payload,
      SETTING_TIMEFRAME,
      messages
    );

    if (success) {
      this.defaultGraphTimeframe = timeframe;
    }
  }

  async onQueryPeriodChange(queryPeriod: string) {
    const period = parseInt(queryPeriod);
    if (period < 5 || period > 3600) {
      const message = `${this.$t(
        'frontend_settings.validation.periodic_query.invalid_period',
        {
          start: 5,
          end: 3600
        }
      )}`;
      this.validateSettingChange(
        SETTING_QUERY_PERIOD,
        'error',
        `${this.$t('frontend_settings.validation.periodic_query.error', {
          message
        })}`
      );
      this.queryPeriod = this.$store.state.settings![QUERY_PERIOD].toString();
      return;
    }

    const message = makeMessage(
      this.$t('frontend_settings.validation.periodic_query.error').toString(),
      this.$t('frontend_settings.validation.periodic_query.success', {
        period
      }).toString()
    );

    const { success } = await this.modifyFrontendSetting(
      {
        [QUERY_PERIOD]: period
      },
      SETTING_QUERY_PERIOD,
      message
    );

    if (success) {
      monitor.stop();
      monitor.start();
    }
  }

  onScrambleDataChange(enabled: boolean) {
    const { commit } = this.$store;
    const previousValue = this.$store.state.session.scrambleData;

    let success: boolean = false;
    let message: string | undefined;

    try {
      commit('session/scrambleData', enabled);
      success = true;
    } catch (error) {
      this.scrambleData = previousValue;
      message = error.message;
    }

    this.validateSettingChange(
      SETTING_SCRAMBLE_DATA,
      success ? 'success' : 'error',
      success
        ? ''
        : `${this.$t('frontend_settings.validation.scramble.error', {
            message
          })}`
    );
  }

  created() {
    this.settingsMessages = settingsMessages(SETTINGS);
  }

  mounted() {
    const state = this.$store.state;
    this.scrambleData = state.session.scrambleData;
    this.defaultGraphTimeframe = state.settings![TIMEFRAME_SETTING];
    this.queryPeriod = state.settings![QUERY_PERIOD].toString();
  }
}
</script>

<style scoped lang="scss"></style>
