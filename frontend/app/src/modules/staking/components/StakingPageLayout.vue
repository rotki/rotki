<script setup lang="ts">
import type { HistoryEventsRestrictions } from '@/modules/history/events/history-events-restrictions';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { asset, error = '', eventsTitle, loading, refresh, restrictions, title } = defineProps<{
  asset: string;
  /** The translated failure message. Nothing is shown while it is empty. */
  error?: string;
  eventsTitle: string;
  loading: boolean;
  refresh: () => Promise<void>;
  restrictions: HistoryEventsRestrictions;
  title: string;
}>();

defineSlots<{
  default: () => unknown;
}>();

const { t } = useI18n({ useScope: 'global' });

const { fetchPrices } = usePriceTaskManager();

async function load(ignoreCache: boolean = false): Promise<void> {
  await Promise.all([
    refresh(),
    fetchPrices({ ignoreCache, selectedAssets: [asset] }),
  ]);
}

onMounted(async () => {
  await load();
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), title]"
    child
  >
    <template #buttons>
      <RuiButton
        variant="outlined"
        color="primary"
        data-testid="staking-refresh"
        :loading="loading"
        @click="load(true)"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-ccw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>
    </template>

    <div class="flex flex-col gap-4">
      <RuiAlert
        v-if="error"
        type="error"
        data-testid="staking-error"
      >
        {{ error }}
      </RuiAlert>

      <slot />

      <HistoryEventsView
        :section-title="eventsTitle"
        :restrictions="restrictions"
      />
    </div>
  </TablePageLayout>
</template>
