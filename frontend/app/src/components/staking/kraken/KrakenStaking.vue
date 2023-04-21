<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { Section } from '@/types/status';

const { events } = toRefs(useKrakenStakingStore());
const { isLoading } = useStatusStore();
const loading = isLoading(Section.STAKING_KRAKEN);
</script>

<template>
  <fragment>
    <v-row>
      <v-col>
        <kraken-staking-overview
          :total-usd="events.totalUsdValue"
          :earned="events.received"
          :loading="loading"
        />
      </v-col>
      <v-col>
        <kraken-staking-received
          :received="events.received"
          :loading="loading"
        />
      </v-col>
    </v-row>
    <history-events-view use-external-account-filter location="kraken" />
  </fragment>
</template>
