<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { Section } from '@/types/status';

const store = useKrakenStakingStore();
const { load, updatePagination } = store;
const { events } = toRefs(store);
const { isLoading } = useStatusStore();
const loading = isLoading(Section.STAKING_KRAKEN);

const refresh = () => load(true);
</script>

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
