<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('trade_history.loading') }}
    </template>
  </progress-screen>
  <v-container v-else>
    <trade-location-selector v-model="selectedLocation" />
    <open-trades v-if="preview" :data="openTrades" />
    <closed-trades
      class="mt-8"
      :data="closedTrades"
      @refresh="fetchTrades(true)"
    />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import ClosedTrades from '@/components/trades/ClosedTrades.vue';
import OpenTrades from '@/components/trades/OpenTrades.vue';
import TradeLocationSelector from '@/components/trades/TradeLocationSelector.vue';
import StatusMixin from '@/mixins/status-mixin';
import { Trade, TradeLocation } from '@/services/trades/types';
import { Section } from '@/store/const';

@Component({
  components: {
    ProgressScreen,
    TradeLocationSelector,
    ClosedTrades,
    OpenTrades
  },
  computed: {
    ...mapState('trades', ['trades'])
  },
  methods: {
    ...mapActions('trades', ['fetchTrades', 'deleteExternalTrade'])
  }
})
export default class TradeHistory extends Mixins(StatusMixin) {
  selectedLocation: TradeLocation | null = null;
  fetchTrades!: (refresh: boolean) => Promise<void>;
  trades!: Trade[];
  openTrades: Trade[] = [];
  section = Section.TRADES;

  get preview(): boolean {
    return !!process.env.VUE_APP_TRADES_PREVIEW;
  }

  get closedTrades(): Trade[] {
    if (!this.selectedLocation) {
      return this.trades;
    }

    return this.trades.filter(
      trade => trade.location === this.selectedLocation
    );
  }

  mounted() {
    this.fetchTrades(false);
  }
}
</script>
