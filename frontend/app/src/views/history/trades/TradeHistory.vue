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
      <closed-trades
        @fetch="fetchTradesHandler"
        @update:payload="onFilterUpdate($event)"
      />
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
import isEqual from 'lodash/isEqual';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import ClosedTrades from '@/components/history/ClosedTrades.vue';
import OpenTrades from '@/components/history/OpenTrades.vue';
import { setupStatusChecking } from '@/composables/common';
import { setupAssociatedLocations, setupTrades } from '@/composables/history';
import { setupSettings } from '@/composables/settings';
import { TradeRequestPayload } from '@/services/history/types';
import { Section } from '@/store/const';
import { TradeEntry } from '@/store/history/types';

export default defineComponent({
  name: 'Trades',
  components: {
    ProgressScreen,
    ClosedTrades,
    OpenTrades
  },
  setup() {
    const { itemsPerPage, refreshPeriod } = setupSettings();
    const { fetchTrades } = setupTrades();
    const { fetchAssociatedLocations } = setupAssociatedLocations();

    const preview = computed<boolean>(() => {
      return !!process.env.VUE_APP_TRADES_PREVIEW;
    });

    const openTrades: TradeEntry[] = [];

    const payload = ref<TradeRequestPayload>({
      limit: itemsPerPage.value,
      offset: 0,
      orderByAttribute: 'time',
      ascending: false
    });

    const fetchTradesHandler = async (refresh: boolean = false) => {
      if (refresh) {
        fetchAssociatedLocations().then();
      }
      await fetchTrades({
        ...payload.value,
        onlyCache: !refresh
      });
    };

    const onFilterUpdate = (newPayload: TradeRequestPayload) => {
      if (!isEqual(payload.value, newPayload)) {
        payload.value = newPayload;
        fetchTradesHandler().then();
      }
    };

    const refreshInterval = ref<any>(null);

    onBeforeMount(async () => {
      fetchAssociatedLocations().then();
      fetchTradesHandler().then();

      const period = refreshPeriod.value * 60 * 1000;

      if (period > 0) {
        refreshInterval.value = setInterval(
          async () => fetchTradesHandler(true),
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
      fetchTradesHandler,
      onFilterUpdate,
      loading: shouldShowLoadingScreen(Section.TRADES)
    };
  }
});
</script>
