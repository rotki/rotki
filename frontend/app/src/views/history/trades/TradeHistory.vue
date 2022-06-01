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
  onUnmounted
} from '@vue/composition-api';
import { get, useIntervalFn } from '@vueuse/core';
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
      return !!import.meta.env.VITE_TRADES_PREVIEW;
    });

    const openTrades: TradeEntry[] = [];

    const period = get(refreshPeriod) * 60 * 1000;

    const { pause, resume, isActive } = useIntervalFn(
      () => {
        fetchTrades(true);
      },
      period,
      { immediate: false }
    );

    onBeforeMount(async () => {
      await fetchTrades();

      if (period > 0) {
        resume();
      }
    });

    onUnmounted(() => {
      if (isActive) pause();
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
