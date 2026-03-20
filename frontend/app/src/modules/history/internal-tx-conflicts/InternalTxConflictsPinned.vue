<script setup lang="ts">
import type { Nullable } from '@rotki/common';
import type { InternalTxConflict } from './types';
import type { Pinned } from '@/types/session';
import { startPromise } from '@shared/utils';
import { HighlightTargetTypes, useHistoryEventNavigation } from '@/composables/history/events/use-history-event-navigation';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import InternalTxConflictsContent from './InternalTxConflictsContent.vue';
import { useInternalTxConflictResolution } from './use-internal-tx-conflict-resolution';

const { highlightedGroupIdentifier, highlightedTxHash } = defineProps<{
  highlightedGroupIdentifier?: string;
  highlightedTxHash?: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const { pinned, showPinned } = storeToRefs(useAreaVisibilityStore());
const { clearAllHighlightTargets, requestNavigation, setHighlightTarget } = useHistoryEventNavigation();
const { cancelResolution, progress } = useInternalTxConflictResolution();

const activeTxHash = ref<string | undefined>(highlightedTxHash);
const isRunning = computed<boolean>(() => get(progress).isRunning);

function setPinned(pin: Nullable<Pinned>): void {
  set(pinned, pin);
}

async function clearHighlight(): Promise<void> {
  set(activeTxHash, undefined);
  clearAllHighlightTargets();
  const { highlightedInternalTxConflict, ...remainingQuery } = get(route).query;
  if (highlightedInternalTxConflict)
    await router.replace({ query: remainingQuery });
}

async function unpin(): Promise<void> {
  await clearHighlight();
  setPinned(null);
}

function closePinnedSidebar(): void {
  startPromise(clearHighlight());
  set(showPinned, false);
}

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

onUnmounted(() => {
  startPromise(clearHighlight());
});
</script>

<template>
  <RuiCard
    no-padding
    class="overflow-hidden !rounded-none h-full flex flex-col"
    variant="flat"
  >
    <div class="flex items-center bg-rui-primary text-white p-2 shrink-0">
      <RuiButton
        variant="text"
        size="sm"
        icon
        @click="closePinnedSidebar()"
      >
        <RuiIcon
          class="text-white"
          name="lu-chevron-right"
          size="20"
        />
      </RuiButton>

      <h6 class="flex items-center text-body-1 pl-2">
        {{ t('internal_tx_conflicts.pinned.title') }}
      </h6>

      <div class="grow" />

      <template v-if="isRunning">
        <span class="text-caption text-white mr-2">
          {{ t('internal_tx_conflicts.resolution.progress', { completed: progress.completed, total: progress.total }) }}
        </span>
        <RuiButton
          variant="text"
          icon
          size="sm"
          @click="cancelResolution()"
        >
          <RuiIcon
            size="20"
            class="text-white"
            name="lu-x"
          />
        </RuiButton>
      </template>
      <template v-else>
        <RuiTooltip
          :popper="{ placement: 'bottom' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              variant="text"
              icon
              size="sm"
              @click="unpin()"
            >
              <RuiIcon
                size="20"
                class="text-white"
                name="lu-pin-off"
              />
            </RuiButton>
          </template>
          {{ t('internal_tx_conflicts.actions.unpin') }}
        </RuiTooltip>
      </template>
    </div>

    <InternalTxConflictsContent
      compact
      :highlighted-tx-hash="activeTxHash"
      @show-in-events="showInHistoryEvents($event)"
    />
  </RuiCard>
</template>
