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

    <v-row class="mt-1">
      <v-col class="grow">
        <v-text-field
          v-model="refreshPeriod"
          outlined
          :disabled="!refreshEnabled"
          type="number"
          min="30"
          :label="$t('frontend_settings.label.refresh')"
          item-value="id"
          item-text="label"
          persistent-hint
          :hint="$t('frontend_settings.hint.refresh')"
          :success-messages="settingsMessages[REFRESH_PERIOD].success"
          :error-messages="settingsMessages[REFRESH_PERIOD].error"
          @change="onRefreshPeriodChange($event)"
        />
      </v-col>
      <v-col class="shrink">
        <v-switch
          v-model="refreshEnabled"
          :label="$t('frontend_settings.label.refresh_enabled')"
          @change="onRefreshPeriodChange($event ? '30' : '-1')"
        />
      </v-col>
    </v-row>

    <div class="text-h6 mt-4">
      {{ $t('frontend_settings.subtitle.query') }}
    </div>

    <v-row class="mt-1">
      <v-col>
        <v-text-field
          v-model="queryPeriod"
          outlined
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
      </v-col>
    </v-row>

    <explorers />
    <theme-manager v-if="premium" />
  </setting-category>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import Explorers from '@/components/settings/explorers/Explorers.vue';
import TimeFrameSettings from '@/components/settings/general/TimeFrameSettings.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import {
  BaseMessage,
  makeMessage,
  settingsMessages
} from '@/components/settings/utils';
import PremiumMixin from '@/mixins/premium-mixin';
import SettingsMixin from '@/mixins/settings-mixin';
import { ThemeManager } from '@/premium/premium';
import { monitor } from '@/services/monitoring';
import {
  QUERY_PERIOD,
  REFRESH_PERIOD,
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
const SETTING_REFRESH_PERIOD = 'refreshPeriod';

const SETTINGS = [
  SETTING_SCRAMBLE_DATA,
  SETTING_TIMEFRAME,
  SETTING_QUERY_PERIOD,
  SETTING_REFRESH_PERIOD
] as const;

type SettingsEntries = typeof SETTINGS[number];

@Component({
  components: {
    ThemeManager,
    Explorers,
    TimeFrameSettings,
    SettingCategory
  }
})
export default class FrontendSettings extends Mixins<
  SettingsMixin<SettingsEntries> & PremiumMixin
>(SettingsMixin, PremiumMixin) {
  queryPeriod: string = '5';
  scrambleData: boolean = false;
  defaultGraphTimeframe: TimeFrameSetting = TIMEFRAME_ALL;
  refreshPeriod: string = '';
  refreshEnabled: boolean = false;

  readonly SCRAMBLE_DATA = SETTING_SCRAMBLE_DATA;
  readonly TIMEFRAME = SETTING_TIMEFRAME;
  readonly QUERY_PERIOD = SETTING_QUERY_PERIOD;
  readonly REFRESH_PERIOD = SETTING_REFRESH_PERIOD;

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
      monitor.restart();
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

  async onRefreshPeriodChange(period: string) {
    const refreshPeriod = parseInt(period);
    const payload: FrontendSettingsPayload = {
      [REFRESH_PERIOD]: refreshPeriod
    };

    const messages: BaseMessage = {
      success:
        refreshPeriod > 0
          ? this.$t('frontend_settings.validation.refresh_period.success', {
              period
            }).toString()
          : this.$t(
              'frontend_settings.validation.refresh_period.success_disabled'
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
      this.refreshPeriod = refreshPeriod < 0 ? '' : period;
      monitor.restart();
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
    const period = state.settings![REFRESH_PERIOD];
    this.refreshEnabled = period > 0;
    this.refreshPeriod = this.refreshEnabled ? period.toString() : '';
  }
}
</script>

<style scoped lang="scss"></style>
