<template>
  <kraken-staking-events
    :events="events"
    :loading="loading"
    @refresh.capture="refresh"
    @update:pagination="updatePagination"
  />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import KrakenStakingEvents from '@/components/staking/kraken/KrakenStakingEvents.vue';
import { setupStatusChecking } from '@/composables/common';
import { Section } from '@/store/const';
import { useKrakenStakingStore } from '@/store/staking/kraken';

export default defineComponent({
  name: 'KrakenStaking',
  components: { KrakenStakingEvents },
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
