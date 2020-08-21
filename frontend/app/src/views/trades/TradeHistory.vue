<template>
  <v-container>
    <trade-location-selector v-if="preview" v-model="selectedLocation" />
    <open-trades v-if="preview" :data="openTrades" />
    <closed-trades class="mt-8" :data="closedTrades" />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import ClosedTrades from '@/components/trades/ClosedTrades.vue';
import OpenTrades from '@/components/trades/OpenTrades.vue';
import TradeLocationSelector from '@/components/trades/TradeLocationSelector.vue';
import { TradeLocation } from '@/components/trades/type';
import { Trade } from '@/services/trades/types';

@Component({
  components: { TradeLocationSelector, ClosedTrades, OpenTrades },
  computed: {
    ...mapState('trades', ['trades'])
  },
  methods: {
    ...mapActions('trades', ['fetchExternalTrades', 'deleteExternalTrade'])
  }
})
export default class TradeHistory extends Vue {
  selectedLocation: TradeLocation | null = 'external';
  fetchExternalTrades!: () => Promise<void>;
  trades!: Trade[];
  openTrades: Trade[] = [];

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
    this.fetchExternalTrades();
  }
}
</script>
