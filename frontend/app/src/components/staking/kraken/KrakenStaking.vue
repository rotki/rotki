<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import Fragment from '@/components/helper/Fragment';

const { events } = toRefs(useKrakenStakingStore());
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
    <history-events-view
      use-external-account-filter
      location="kraken"
      :entry-types="[HistoryEventEntryType.HISTORY_EVENT]"
    />
  </fragment>
</template>
