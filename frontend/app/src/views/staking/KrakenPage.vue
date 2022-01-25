<template>
  <div>
    <progress-screen v-if="loading">
      <template #message>
        {{ $t('kraken_page.loading') }}
      </template>
    </progress-screen>
    <div v-else>
      <kraken-staking />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, onBeforeMount } from '@vue/composition-api';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import KrakenStaking from '@/components/staking/kraken/KrakenStaking.vue';
import { setupStatusChecking } from '@/composables/common';
import { Section } from '@/store/const';
import { useKrakenStakingStore } from '@/store/staking/kraken';

export default defineComponent({
  name: 'KrakenPage',
  components: { KrakenStaking, ProgressScreen },
  setup() {
    const { shouldShowLoadingScreen } = setupStatusChecking();
    const { load } = useKrakenStakingStore();

    onBeforeMount(async () => await load(false));

    return {
      loading: shouldShowLoadingScreen(Section.STAKING_KRAKEN)
    };
  }
});
</script>
