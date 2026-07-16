<script setup lang="ts">
import type { InternalTxConflict } from './types';
import { startPromise } from '@shared/utils';
import { HighlightTargetTypes, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';
import { PinnedNames } from '@/modules/session/types';
import InternalTxConflictRepullSettings from '@/modules/settings/general/InternalTxConflictRepullSettings.vue';
import { usePinnedHighlightNavigation } from '@/modules/shell/pinned/use-pinned-highlight-navigation';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';
import InternalTxConflictsContent from './InternalTxConflictsContent.vue';
import { useInternalTxConflictsPanel } from './use-internal-tx-conflicts-panel';

const { highlightedGroupIdentifier, highlightedTxHash } = defineProps<{
  highlightedGroupIdentifier?: string;
  highlightedTxHash?: string;
}>();

const { isPinned } = usePinnedPanel(PinnedNames.INTERNAL_TX_CONFLICTS);
const { requestNavigation, setHighlightTarget } = useHistoryEventNavigation();
const { showSettings } = useInternalTxConflictsPanel();

const activeTxHash = ref<string | undefined>(highlightedTxHash);

const { clearHighlight } = usePinnedHighlightNavigation(
  ['highlightedInternalTxConflict'],
  () => set(activeTxHash, undefined),
  () => get(isPinned),
);

function navigateToHighlight(groupIdentifier: string, txHash: string): void {
  set(activeTxHash, txHash);
  setHighlightTarget(HighlightTargetTypes.INTERNAL_TX_CONFLICT, { groupIdentifier, identifier: 0 });
  requestNavigation({
    highlightedInternalTxConflict: groupIdentifier,
    targetGroupIdentifier: groupIdentifier,
  });
}

function showInHistoryEvents(conflict: InternalTxConflict): void {
  if (!conflict.groupIdentifier)
    return;

  if (get(activeTxHash) === conflict.txHash) {
    startPromise(clearHighlight());
    return;
  }

  navigateToHighlight(conflict.groupIdentifier, conflict.txHash);
}

onBeforeMount(() => {
  if (highlightedGroupIdentifier && highlightedTxHash)
    navigateToHighlight(highlightedGroupIdentifier, highlightedTxHash);
});

watch([() => highlightedGroupIdentifier, () => highlightedTxHash], ([newGroupId, newHash], [oldGroupId]) => {
  if (newGroupId && newHash && newGroupId !== oldGroupId)
    navigateToHighlight(newGroupId, newHash);
});
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <div
      v-if="showSettings"
      class="px-3 pt-2 border-b border-default shrink-0"
    >
      <InternalTxConflictRepullSettings compact />
    </div>

    <div class="flex-1 min-h-0">
      <InternalTxConflictsContent
        compact
        :highlighted-tx-hash="activeTxHash"
        @show-in-events="showInHistoryEvents($event)"
      />
    </div>
  </div>
</template>
