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
      :visible-timeframes="visibleTimeframes"
      :current-session-timeframe="currentSessionTimeframe"
      @timeframe-change="onTimeframeChange"
      @visible-timeframes-change="onVisibleTimeframesChange"
    />

    <div class="text-h6 mt-4">
      {{ $t('frontend_settings.subtitle.graph_basis') }}
    </div>

    <v-switch
      v-model="zeroBased"
      class="general-settings__fields__zero-base mb-4"
      :label="$t('frontend_settings.label.zero_based')"
      :hint="$t('frontend_settings.label.zero_based_hint')"
      persistent-hint
      :success-messages="settingsMessages[GRAPH_ZERO_BASED].success"
      :error-messages="settingsMessages[GRAPH_ZERO_BASED].error"
      @change="onZeroBasedUpdate($event)"
    />

    <div class="text-h6 mt-4">
      {{ $t('frontend_settings.subtitle.include_nfts') }}
    </div>
    <v-switch
      v-model="includeNfts"
      class="general-settings__fields__zero-base mb-4"
      :label="$t('frontend_settings.label.include_nfts')"
      :hint="$t('frontend_settings.label.include_nfts_hint')"
      persistent-hint
      :success-messages="settingsMessages[NFTS_IN_NET_VALUE].success"
      :error-messages="settingsMessages[NFTS_IN_NET_VALUE].error"
      @change="onIncludeNftChange($event)"
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
    <theme-manager-lock v-else />
  </setting-category>
</template>

<script lang="ts">
import {
  TimeFramePeriod,
  TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ThemeManagerLock from '@/components/premium/ThemeManagerLock.vue';
import Explorers from '@/components/settings/explorers/Explorers.vue';
import TimeFrameSettings from '@/components/settings/general/TimeFrameSettings.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import {
  BaseMessage,
  makeMessage,
  settingsMessages
} from '@/components/settings/utils';
import { Constraints } from '@/data/constraints';
import PremiumMixin from '@/mixins/premium-mixin';
import SettingsMixin from '@/mixins/settings-mixin';
import { ThemeManager } from '@/premium/premium';
import { monitor } from '@/services/monitoring';
import {
  FrontendSettingsPayload,
  GRAPH_ZERO_BASED,
  NFTS_IN_NET_VALUE,
  QUERY_PERIOD,
  REFRESH_PERIOD,
  TIMEFRAME_SETTING,
  VISIBLE_TIMEFRAMES
} from '@/types/frontend-settings';

const SETTING_SCRAMBLE_DATA = 'scrambleData';
const SETTING_TIMEFRAME = 'timeframe';
const SETTING_VISIBLE_TIMEFRAMES = 'visibleTimeframes';
const SETTING_QUERY_PERIOD = 'queryPeriod';
const SETTING_REFRESH_PERIOD = 'refreshPeriod';

const SETTINGS = [
  SETTING_SCRAMBLE_DATA,
  SETTING_TIMEFRAME,
  SETTING_VISIBLE_TIMEFRAMES,
  SETTING_QUERY_PERIOD,
  SETTING_REFRESH_PERIOD,
  GRAPH_ZERO_BASED,
  NFTS_IN_NET_VALUE
] as const;

const MAX_REFRESH_PERIOD = Constraints.MAX_MINUTES_DELAY;

type SettingsEntries = typeof SETTINGS[number];

@Component({
  components: {
    ThemeManagerLock,
    ThemeManager,
    Explorers,
    TimeFrameSettings,
    SettingCategory
  },
  methods: {
    ...mapActions('statistics', ['fetchNetValue'])
  }
})
export default class FrontendSettings extends Mixins<
  SettingsMixin<SettingsEntries> & PremiumMixin
>(SettingsMixin, PremiumMixin) {
  queryPeriod: string = '5';
  scrambleData: boolean = false;
  defaultGraphTimeframe: TimeFrameSetting = TimeFramePeriod.ALL;
  visibleTimeframes: TimeFrameSetting[] = [];
  currentSessionTimeframe: TimeFramePeriod = TimeFramePeriod.ALL;
  refreshPeriod: string = '';
  refreshEnabled: boolean = false;
  zeroBased: boolean = false;
  includeNfts: boolean = true;
  fetchNetValue!: () => Promise<void>;

  readonly SCRAMBLE_DATA = SETTING_SCRAMBLE_DATA;
  readonly TIMEFRAME = SETTING_TIMEFRAME;
  readonly QUERY_PERIOD = SETTING_QUERY_PERIOD;
  readonly REFRESH_PERIOD = SETTING_REFRESH_PERIOD;
  readonly GRAPH_ZERO_BASED = GRAPH_ZERO_BASED;
  readonly NFTS_IN_NET_VALUE = NFTS_IN_NET_VALUE;

  async onZeroBasedUpdate(enabled: boolean) {
    const payload: FrontendSettingsPayload = {
      [GRAPH_ZERO_BASED]: enabled
    };

    const messages: BaseMessage = {
      success: '',
      error: ''
    };

    await this.modifyFrontendSetting(payload, GRAPH_ZERO_BASED, messages);
  }

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

  async onVisibleTimeframesChange(timeframes: TimeFrameSetting[]) {
    const payload: FrontendSettingsPayload = {
      [VISIBLE_TIMEFRAMES]: timeframes
    };

    const messages: BaseMessage = {
      success: '',
      error: ''
    };

    const { success } = await this.modifyFrontendSetting(
      payload,
      SETTING_VISIBLE_TIMEFRAMES,
      messages
    );

    if (success) {
      this.visibleTimeframes = timeframes;
    }
  }

  async onIncludeNftChange(include: boolean) {
    const payload: FrontendSettingsPayload = {
      [NFTS_IN_NET_VALUE]: include
    };

    const messages: BaseMessage = {
      success: '',
      error: ''
    };

    await this.modifyFrontendSetting(payload, NFTS_IN_NET_VALUE, messages);
    await this.fetchNetValue();
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
      this.validateSettingChange(SETTING_QUERY_PERIOD, 'error', message);
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
    } catch (error: any) {
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
    if (refreshPeriod > MAX_REFRESH_PERIOD) {
      const message = `${this.$t(
        'frontend_settings.validation.refresh_period.invalid_period',
        {
          start: 1,
          end: MAX_REFRESH_PERIOD
        }
      )}`;

      this.validateSettingChange(SETTING_REFRESH_PERIOD, 'error', message);
      this.refreshPeriod =
        this.$store.state.settings![REFRESH_PERIOD].toString();
      return;
    }

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
      this.refreshPeriod = refreshPeriod > 0 ? period : '';
      this.refreshEnabled = !!this.refreshPeriod;
      monitor.restart();
    }
  }

  created() {
    this.settingsMessages = settingsMessages(SETTINGS);
  }

  mounted() {
    const state = this.$store.state;
    this.scrambleData = state.session.scrambleData;
    this.currentSessionTimeframe = state.session.timeframe;
    this.defaultGraphTimeframe = state.settings![TIMEFRAME_SETTING];
    this.visibleTimeframes = state.settings![VISIBLE_TIMEFRAMES];
    this.queryPeriod = state.settings![QUERY_PERIOD].toString();
    const period = state.settings![REFRESH_PERIOD];
    this.zeroBased = state.settings![GRAPH_ZERO_BASED];
    this.refreshEnabled = period > 0;
    this.refreshPeriod = this.refreshEnabled ? period.toString() : '';
    this.includeNfts = state.settings![NFTS_IN_NET_VALUE];
  }
}
</script>
