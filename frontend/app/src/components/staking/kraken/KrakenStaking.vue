<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import Fragment from '@/components/helper/Fragment';

const { events } = toRefs(useKrakenStakingStore());
</script>

<template>
  <Fragment>
    <VRow>
      <VCol>
        <KrakenStakingOverview
          :total-usd="events.totalUsdValue"
          :earned="events.received"
        />
      </VCol>
      <VCol>
        <KrakenStakingReceived :received="events.received" />
      </VCol>
    </VRow>

    <!-- as an exception here we specify event-types to only include staking events  -->
    <!-- if an alternative way becomes possible we can use that -->
    <HistoryEventsView
      use-external-account-filter
      location="kraken"
      :event-types="['staking']"
      :entry-types="[HistoryEventEntryType.HISTORY_EVENT]"
    />
  </Fragment>
</template>
