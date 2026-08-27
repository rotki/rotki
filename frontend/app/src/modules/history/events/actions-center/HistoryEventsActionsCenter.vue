<script setup lang="ts">
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import type { DialogShowOptions } from '@/modules/history/events/dialog-types';
import { startPromise } from '@shared/utils';
import ActionCenterList from '@/modules/core/action-center/ActionCenterList.vue';
import ActionCenterMenu from '@/modules/core/action-center/ActionCenterMenu.vue';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { type HistoryEventIssue, type HistoryIssueTarget, useHistoryEventIssues } from '@/modules/history/events/actions-center/use-history-event-issues';
import { useUndecodedTransactionsCount } from '@/modules/history/events/tx/use-undecoded-transactions-count';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';

const emit = defineEmits<{
  'show:dialog': [options: DialogShowOptions];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const open = ref<boolean>(false);

const { processing } = useHistoryEventsStatus();
const { autoMatchLoading } = useUnmatchedAssetMovements();
const { autoMatchLoading: bridgeAutoMatchLoading } = useUnmatchedBridgeTransactions();
const {
  activeItems,
  categoryCount,
  checking,
  clearedItems,
  lockedItems,
  refreshAll,
  refreshing,
  reviewItems,
} = useHistoryEventIssues();
const { fetchUndecodedTransactionsBreakdown } = useUndecodedTransactionsCount();
const { pinPanel } = useAreaVisibilityStore();

const settled = useRefWithDebounce(logicOr(processing, autoMatchLoading, bridgeAutoMatchLoading), 200);

const rows = computed<HistoryEventIssue[]>(() => [...get(activeItems), ...get(reviewItems), ...get(lockedItems)]);

async function openDuplicates(groupIds: string[], status: DuplicateHandlingStatus): Promise<void> {
  await router.push({
    name: '/history/events/',
    query: {
      duplicateHandlingStatus: status,
      groupIdentifiers: groupIds.join(','),
    },
  });
}

function openTarget(target: HistoryIssueTarget): void {
  set(open, false);
  switch (target.kind) {
    case 'dialog':
      emit('show:dialog', target.options);
      break;
    case 'duplicates':
      startPromise(openDuplicates(target.groupIds, target.status));
      break;
    case 'pin':
      pinPanel(target.panel);
      break;
    case 'route':
      startPromise(router.push(target.to));
      break;
    case 'run':
      target.run();
      break;
  }
}

watchImmediate(settled, (busy) => {
  if (!busy) {
    startPromise(refreshAll());
  }
});

onMounted(() => {
  startPromise(fetchUndecodedTransactionsBreakdown());
});
</script>

<template>
  <ActionCenterMenu
    v-model="open"
    :count="categoryCount"
    :checking="checking"
  >
    <ActionCenterList
      :items="rows"
      :cleared="clearedItems"
      :count="categoryCount"
      :checking="checking"
      :refreshing="refreshing"
      :checking-hint="t('transactions.alerts.subtitle_checking')"
      :clear-hint="t('transactions.alerts.subtitle_clear')"
      @open="openTarget($event)"
      @refresh="startPromise(refreshAll())"
    />
  </ActionCenterMenu>
</template>
