<script setup lang="ts">
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import type { DialogShowOptions } from '@/modules/history/events/dialog-types';
import { startPromise } from '@shared/utils';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import HistoryEventsActionsList from '@/modules/history/events/actions-center/HistoryEventsActionsList.vue';
import { type HistoryIssueTarget, useHistoryEventIssues } from '@/modules/history/events/actions-center/use-history-event-issues';
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
const { categoryCount, checking, hasIssues, refreshAll } = useHistoryEventIssues();
const { fetchUndecodedTransactionsBreakdown } = useUndecodedTransactionsCount();
const { pinPanel } = useAreaVisibilityStore();

const settled = useRefWithDebounce(logicOr(processing, autoMatchLoading, bridgeAutoMatchLoading), 200);

const tooltip = computed<string>(() => get(checking)
  ? t('transactions.alerts.button_checking')
  : t('transactions.alerts.button_clear'));

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
  if (target.kind === 'dialog') {
    emit('show:dialog', target.options);
  }
  else if (target.kind === 'pin') {
    // `pinPanel` focuses the tab and reveals the rail, so the panel opens beside
    // the table whether or not it was already pinned.
    pinPanel(target.panel);
  }
  else {
    startPromise(openDuplicates(target.groupIds, target.status));
  }
}

// Counts only settle once the history work (tx query, exchange events, decoding,
// matching) is idle, so a scan runs whenever that settles - including right away
// when the page opens on an already-synced session, which is why this is
// `watchImmediate` and not tied to a sync-completion signal.
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
  <RuiMenu
    v-model="open"
    :popper="{ placement: 'bottom-end' }"
    menu-class="w-[36rem] max-w-[90vw]"
  >
    <template #activator="{ attrs }">
      <RuiButton
        v-if="hasIssues"
        size="lg"
        variant="outlined"
        color="warning"
        class="!rounded-full !bg-rui-warning/10 [&>span]:!hidden lg:[&>span]:!inline"
        data-testid="actions-center-button"
        v-bind="attrs"
      >
        <template #prepend>
          <RuiIcon
            name="lu-triangle-alert"
            size="18"
          />
        </template>

        {{ t('transactions.alerts.button') }}

        <template #append>
          <span
            class="ml-1 min-w-5 px-1.5 rounded-full bg-rui-warning text-white text-caption font-medium leading-5 text-center"
            data-testid="actions-center-button-count"
          >
            {{ categoryCount }}
          </span>
        </template>
      </RuiButton>

      <RuiTooltip
        v-else
        :popper="{ placement: 'bottom' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            size="lg"
            class="!text-rui-text-secondary"
            data-testid="actions-center-button"
            :aria-label="tooltip"
            v-bind="attrs"
          >
            <!-- static icon on purpose: the sync panel and the pending-task list already
                 carry the motion, a third spinner here would only add noise -->
            <RuiIcon :name="checking ? 'lu-circle-dashed' : 'lu-circle-check'" />
          </RuiButton>
        </template>
        {{ tooltip }}
      </RuiTooltip>
    </template>

    <HistoryEventsActionsList @open="openTarget($event)" />
  </RuiMenu>
</template>
