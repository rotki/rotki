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

<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import KrakenStakingEvents from '@/components/staking/kraken/KrakenStakingEvents.vue';
import KrakenStakingOverview from '@/components/staking/kraken/KrakenStakingOverview.vue';
import KrakenStakingReceived from '@/components/staking/kraken/KrakenStakingReceived.vue';
import { useSectionLoading } from '@/composables/common';
import { useKrakenStakingStore } from '@/store/staking/kraken';
import { Section } from '@/types/status';

const store = useKrakenStakingStore();
const { load, updatePagination } = store;
const { events } = toRefs(store);
const { isSectionRefreshing } = useSectionLoading();
const loading = isSectionRefreshing(Section.STAKING_KRAKEN);

const refresh = () => load(true);
</script>
