<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('trade_history.loading') }}
    </template>
    {{ $t('trade_history.loading_subtitle') }}
  </progress-screen>
  <v-container v-else>
    <trade-location-selector
      v-model="selectedLocation"
      :available-locations="availableLocations"
    />
    <open-trades v-if="preview" :data="openTrades" />
    <closed-trades class="mt-8" :data="closedTrades" @refresh="refresh" />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import ClosedTrades from '@/components/history/ClosedTrades.vue';
import OpenTrades from '@/components/history/OpenTrades.vue';
import TradeLocationSelector from '@/components/history/TradeLocationSelector.vue';
import StatusMixin from '@/mixins/status-mixin';
import { TradeLocation } from '@/services/history/types';
import { Section } from '@/store/const';
import {
  FETCH_FROM_CACHE,
  FETCH_FROM_SOURCE,
  FETCH_REFRESH,
  HistoryActions
} from '@/store/history/consts';
import { FetchSource, TradeEntry } from '@/store/history/types';
import { REFRESH_PERIOD } from '@/store/settings/consts';
import { RefreshPeriod } from '@/store/settings/types';

@Component({
  components: {
    ProgressScreen,
    TradeLocationSelector,
    ClosedTrades,
    OpenTrades
  },
  computed: {
    ...mapGetters('history', ['trades']),
    ...mapState('settings', [REFRESH_PERIOD])
  },
  methods: {
    ...mapActions('history', [HistoryActions.FETCH_TRADES]),
    ...mapActions('defi', ['fetchUniswapTrades', 'fetchBalancerTrades'])
  }
})
export default class TradeHistory extends Mixins(StatusMixin) {
  selectedLocation: TradeLocation | null = null;
  [HistoryActions.FETCH_TRADES]!: (payload: FetchSource) => Promise<void>;
  fetchUniswapTrades!: (refresh: boolean) => Promise<void>;
  fetchBalancerTrades!: (refresh: boolean) => Promise<void>;
  [REFRESH_PERIOD]!: RefreshPeriod;
  trades!: TradeEntry[];
  openTrades: TradeEntry[] = [];
  section = Section.TRADES;
  refreshInterval: any;

  get preview(): boolean {
    return !!process.env.VUE_APP_TRADES_PREVIEW;
  }

  get availableLocations(): TradeLocation[] {
    return this.trades
      .map(trade => trade.location)
      .filter((value, index, array) => array.indexOf(value) === index);
  }

  get closedTrades(): TradeEntry[] {
    if (!this.selectedLocation) {
      return this.trades;
    }

    return this.trades.filter(
      trade => trade.location === this.selectedLocation
    );
  }

  created() {
    const period = this[REFRESH_PERIOD] * 60 * 1000;
    if (period > 0) {
      this.refreshInterval = setInterval(async () => this.refresh(), period);
    }
  }

  destroyed() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  async mounted() {
    await this.load();
  }

  private async load() {
    await Promise.all([
      this.fetchTrades(FETCH_FROM_CACHE),
      this.fetchUniswapTrades(false),
      this.fetchBalancerTrades(false)
    ]);
    await this.fetchTrades(FETCH_FROM_SOURCE);
  }

  private async refresh() {
    await Promise.all([
      this.fetchTrades(FETCH_REFRESH),
      this.fetchUniswapTrades(true),
      this.fetchBalancerTrades(true)
    ]);
  }
}
</script>
