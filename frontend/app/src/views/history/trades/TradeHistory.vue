<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('trade_history.loading') }}
    </template>
    {{ $t('trade_history.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <open-trades v-if="preview" :data="openTrades" />
    <div class="mt-8">
      <closed-trades @fetch="fetchTrades" />
    </div>
  </div>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onBeforeMount,
  onUnmounted,
  ref
} from '@vue/composition-api';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import ClosedTrades from '@/components/history/ClosedTrades.vue';
import OpenTrades from '@/components/history/OpenTrades.vue';
import { setupStatusChecking } from '@/composables/common';
import { setupSettings } from '@/composables/settings';
import { Section } from '@/store/const';
import { useTrades } from '@/store/history';
import { TradeEntry } from '@/store/history/types';

export default defineComponent({
  name: 'Trades',
  components: {
    ProgressScreen,
    ClosedTrades,
    OpenTrades
  },
  setup() {
    const { refreshPeriod } = setupSettings();
    const { fetchTrades } = useTrades();

    const preview = computed<boolean>(() => {
      return !!process.env.VUE_APP_TRADES_PREVIEW;
    });

    const openTrades: TradeEntry[] = [];

    const refreshInterval = ref<any>(null);

    onBeforeMount(async () => {
      await fetchTrades();

      const period = refreshPeriod.value * 60 * 1000;

      if (period > 0) {
        refreshInterval.value = setInterval(
          async () => fetchTrades(true),
          period
        );
      }
    });

    onUnmounted(() => {
      if (refreshInterval.value) {
        clearInterval(refreshInterval.value);
      }
    });

    const { shouldShowLoadingScreen } = setupStatusChecking();

    return {
      preview,
      openTrades,
      fetchTrades,
      loading: shouldShowLoadingScreen(Section.TRADES)
    };
  }
});
</script>
