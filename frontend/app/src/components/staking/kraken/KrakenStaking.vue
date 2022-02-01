<template>
  <fragment>
    <v-row>
      <v-col>
        <kraken-staking-overview
          :total-usd="events.totalUsdValue"
          :earned="events.received"
        />
      </v-col>
      <v-col>
        <kraken-staking-received :received="events.received" />
      </v-col>
    </v-row>
    <kraken-staking-events
      class="mt-4"
      :events="events"
      :loading="loading"
      @refresh.capture="refresh"
      @update:pagination="updatePagination"
    />
  </fragment>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import Fragment from '@/components/helper/Fragment';
import KrakenStakingEvents from '@/components/staking/kraken/KrakenStakingEvents.vue';
import KrakenStakingOverview from '@/components/staking/kraken/KrakenStakingOverview.vue';
import KrakenStakingReceived from '@/components/staking/kraken/KrakenStakingReceived.vue';
import { setupStatusChecking } from '@/composables/common';
import { Section } from '@/store/const';
import { useKrakenStakingStore } from '@/store/staking/kraken';

export default defineComponent({
  name: 'KrakenStaking',
  components: {
    KrakenStakingReceived,
    KrakenStakingOverview,
    Fragment,
    KrakenStakingEvents
  },
  setup() {
    const store = useKrakenStakingStore();
    const { events } = storeToRefs(store);
    const { isSectionRefreshing } = setupStatusChecking();

    const { load, updatePagination } = store;
    const refresh = () => load(true);
    return {
      events,
      loading: isSectionRefreshing(Section.STAKING_KRAKEN),
      refresh,
      updatePagination
    };
  }
});
</script>
