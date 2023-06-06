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

    <!-- as an exception here we specify event-types to only include staking events  -->
    <!-- if an alternative way becomes possible we can use that -->
    <history-events-view
      use-external-account-filter
      location="kraken"
      :event-types="['staking']"
      :entry-types="[HistoryEventEntryType.HISTORY_EVENT]"
    />
  </fragment>
</template>
