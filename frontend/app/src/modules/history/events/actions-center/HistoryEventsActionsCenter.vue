<script setup lang="ts">
import type { DialogShowOptions } from '@/modules/history/events/dialog-types';
import { startPromise } from '@shared/utils';
import ActionCenterList from '@/modules/core/action-center/ActionCenterList.vue';
import ActionCenterMenu from '@/modules/core/action-center/ActionCenterMenu.vue';
import { useOpenActionTarget } from '@/modules/core/action-center/use-open-action-target';
import { duplicatesRoute } from '@/modules/history/events/actions-center/history-issue-routes';
import { type HistoryEventIssue, type HistoryIssueTarget, useHistoryEventIssues } from '@/modules/history/events/actions-center/use-history-event-issues';
import { useUndecodedTransactionsCount } from '@/modules/history/events/tx/use-undecoded-transactions-count';

const emit = defineEmits<{
  'show:dialog': [options: DialogShowOptions];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const open = ref<boolean>(false);

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
const { openTarget: openActionTarget } = useOpenActionTarget();

const rows = computed<HistoryEventIssue[]>(() => [...get(activeItems), ...get(reviewItems), ...get(lockedItems)]);

/**
 * Resolves a row's target on the history events page.
 *
 * @remarks
 * This view sits beside the page's dialogs, so a dialog opens in place instead of through the route
 * the global center uses to reach it from elsewhere.
 */
function openTarget(target: HistoryIssueTarget): void {
  const close = (): void => set(open, false);
  switch (target.kind) {
    case 'dialog':
      close();
      emit('show:dialog', target.options);
      break;
    case 'duplicates':
      close();
      startPromise(router.push(duplicatesRoute(target.groupIds, target.status)));
      break;
    default:
      openActionTarget(target, close);
  }
}

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
