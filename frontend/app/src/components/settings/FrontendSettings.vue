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

    <div class="text-h6">
      {{ $t('frontend_settings.subtitle.refresh') }}
    </div>

    <v-select
      v-model="refreshPeriod"
      :items="refreshOptions"
      :label="$t('frontend_settings.label.refresh')"
      item-value="id"
      item-text="label"
      persistent-hint
      :hint="$t('frontend_settings.hint.refresh')"
      :success-messages="settingsMessages[REFRESH_PERIOD].success"
      :error-messages="settingsMessages[REFRESH_PERIOD].error"
      @change="onRefreshPeriodChange($event)"
    />

    <div class="text-h6 mt-4">
      {{ $t('frontend_settings.subtitle.query') }}
    </div>

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
  REFRESH_1H,
  REFRESH_2H,
  REFRESH_30MIN,
  REFRESH_NONE,
  REFRESH_PERIOD,
  TIMEFRAME_ALL,
  TIMEFRAME_SETTING
} from '@/store/settings/consts';
import {
  FrontendSettingsPayload,
  RefreshPeriod,
  TimeFrameSetting
} from '@/store/settings/types';

const SETTING_SCRAMBLE_DATA = 'scrambleData';
const SETTING_TIMEFRAME = 'timeframe';
const SETTING_QUERY_PERIOD = 'queryPeriod';
const SETTING_REFRESH_PERIOD = 'refreshPeriod';

const SETTINGS = [
  SETTING_SCRAMBLE_DATA,
  SETTING_TIMEFRAME,
  SETTING_QUERY_PERIOD,
  SETTING_REFRESH_PERIOD
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
  refreshPeriod: RefreshPeriod = REFRESH_NONE;

  readonly SCRAMBLE_DATA = SETTING_SCRAMBLE_DATA;
  readonly TIMEFRAME = SETTING_TIMEFRAME;
  readonly QUERY_PERIOD = SETTING_QUERY_PERIOD;
  readonly REFRESH_PERIOD = SETTING_REFRESH_PERIOD;

  readonly refreshOptions = [
    {
      label: this.$t('frontend_settings.refresh.none').toString(),
      id: REFRESH_NONE
    },
    {
      label: this.$t('frontend_settings.refresh.30min').toString(),
      id: REFRESH_30MIN
    },
    {
      label: this.$t('frontend_settings.refresh.1h').toString(),
      id: REFRESH_1H
    },
    {
      label: this.$t('frontend_settings.refresh.2h').toString(),
      id: REFRESH_2H
    }
  ];

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

  async onRefreshPeriodChange(period: RefreshPeriod) {
    const payload: FrontendSettingsPayload = {
      [REFRESH_PERIOD]: period
    };

    const messages: BaseMessage = {
      success: this.$t(
        'frontend_settings.validation.refresh_period.success'
      ).toString(),
      error: this.$t(
        'frontend_settings.validation.refresh_period.error'
      ).toString()
    };

    const { success } = await this.modifyFrontendSetting(
      payload,
      SETTING_REFRESH_PERIOD,
      messages
    );
    if (success) {
      monitor.stop();
      monitor.start();
    }
  }

  created() {
    this.settingsMessages = settingsMessages(SETTINGS);
  }

  mounted() {
    const state = this.$store.state;
    this.scrambleData = state.session.scrambleData;
    this.defaultGraphTimeframe = state.settings![TIMEFRAME_SETTING];
    this.queryPeriod = state.settings![QUERY_PERIOD].toString();
    this.refreshPeriod = state.settings![REFRESH_PERIOD];
  }
}
</script>

<style scoped lang="scss"></style>
