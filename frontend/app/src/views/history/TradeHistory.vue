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
    <closed-trades
      class="mt-8"
      :data="closedTrades"
      @refresh="fetchTrades(true)"
    />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import ClosedTrades from '@/components/history/ClosedTrades.vue';
import OpenTrades from '@/components/history/OpenTrades.vue';
import TradeLocationSelector from '@/components/history/TradeLocationSelector.vue';
import StatusMixin from '@/mixins/status-mixin';
import { Trade, TradeLocation } from '@/services/history/types';
import { Section } from '@/store/const';

@Component({
  components: {
    ProgressScreen,
    TradeLocationSelector,
    ClosedTrades,
    OpenTrades
  },
  computed: {
    ...mapGetters('history', ['trades'])
  },
  methods: {
    ...mapActions('history', ['fetchTrades', 'deleteExternalTrade'])
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

  get availableLocations(): TradeLocation[] {
    return this.trades
      .map(trade => trade.location)
      .filter((value, index, array) => array.indexOf(value) === index);
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
