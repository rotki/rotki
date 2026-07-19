<script setup lang="ts">
import { Section } from '@/modules/core/common/status';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useInternalTxConflicts } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflicts';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { useStatusUpdater } from '@/modules/shell/sync-progress/use-status-updater';

const show = defineModel<boolean>('show', { required: true });

const { processing, mainPage } = defineProps<{
  processing: boolean;
  mainPage: boolean;
}>();

const emit = defineEmits<{
  'open:match-asset-movements': [];
  'open:match-bridge-transactions': [];
  'open:internal-tx-conflicts': [];
  'open:decoding-status': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const { isFirstLoad } = useStatusUpdater(Section.HISTORY);

const {
  autoMatchLoading,
  loading: unmatchedLoading,
  refreshUnmatchedAssetMovements,
  unmatchedCount,
} = useUnmatchedAssetMovements();

const {
  autoMatchLoading: bridgeAutoMatchLoading,
  loading: unmatchedBridgesLoading,
  refreshUnmatchedBridgeTransactions,
  unmatchedCount: unmatchedBridgesCount,
} = useUnmatchedBridgeTransactions();

const loading = useRefWithDebounce(logicOr(() => processing, autoMatchLoading, bridgeAutoMatchLoading), 200);

const {
  autoFixCount,
  autoFixGroupIds,
  fetchCustomizedEventDuplicates,
  loading: duplicatesLoading,
  manualReviewCount,
  manualReviewGroupIds,
} = useCustomizedEventDuplicates();

const { fetchCounts, issueCount: internalConflictsCount } = useInternalTxConflicts();
const { decodingStatus } = storeToRefs(useDecodingStatusStore());

const undecodedCount = computed<number>(() => {
  if (processing)
    return 0;
  return get(decodingStatus).reduce((sum, { processed, total }) => sum + Math.max(0, total - processed), 0);
});

const showUnmatchedMovements = computed<boolean>(() => !get(autoMatchLoading) && get(unmatchedCount) > 0);
const showUnmatchedBridges = computed<boolean>(() => !get(bridgeAutoMatchLoading) && get(unmatchedBridgesCount) > 0);
const showAutoFixDuplicates = computed<boolean>(() => get(autoFixCount) > 0);
const showManualReviewDuplicates = computed<boolean>(() => get(manualReviewCount) > 0);
const showInternalConflicts = computed<boolean>(() => get(internalConflictsCount) > 0);
const showUndecoded = computed<boolean>(() => get(undecodedCount) > 0);

const hasAlerts = logicOr(showUnmatchedMovements, showUnmatchedBridges, showAutoFixDuplicates, showManualReviewDuplicates, showInternalConflicts, showUndecoded);
const refreshing = logicOr(unmatchedLoading, unmatchedBridgesLoading, duplicatesLoading);

const showAlerts = logicAnd(() => mainPage, hasAlerts, show);

function closeAlerts(): void {
  set(show, false);
}

function openMatchAssetMovements(): void {
  closeAlerts();
  emit('open:match-asset-movements');
}

function openMatchBridgeTransactions(): void {
  closeAlerts();
  emit('open:match-bridge-transactions');
}

function openInternalTxConflicts(): void {
  closeAlerts();
  emit('open:internal-tx-conflicts');
}

function openDecodingStatus(): void {
  closeAlerts();
  emit('open:decoding-status');
}

async function viewDuplicates(groupIds: string[], status: DuplicateHandlingStatus): Promise<void> {
  closeAlerts();
  const groupIdentifiers = groupIds.join(',');
  await router.push({
    name: '/history/events/',
    query: {
      duplicateHandlingStatus: status,
      groupIdentifiers,
    },
  });
}

watchImmediate(loading, async (isLoading) => {
  if (!isLoading && mainPage && !isFirstLoad()) {
    await Promise.all([
      refreshUnmatchedAssetMovements(),
      refreshUnmatchedBridgeTransactions(),
      fetchCustomizedEventDuplicates(),
      fetchCounts(),
    ]);
  }
});
</script>

<template>
  <div class="relative">
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="showAlerts"
          class="fixed inset-0 bg-black/30 z-40"
          @click="closeAlerts()"
        />
      </Transition>
    </Teleport>
    <RuiAlert
      v-if="showAlerts"
      type="warning"
      class="absolute top-0 left-0 right-0 z-50 shadow-lg overflow-hidden"
      closeable
      @close="closeAlerts()"
    >
      <template #title>
        {{ t('transactions.alerts.title') }}
      </template>

      <RuiProgress
        v-if="refreshing"
        thickness="2"
        color="primary"
        variant="indeterminate"
        class="absolute top-0 left-0 w-full"
      />
      <ul class="list-disc pl-4">
        <li v-if="showUnmatchedMovements">
          <div class="flex items-center">
            <span>{{ t('asset_movement_matching.banner.message', { count: unmatchedCount }) }}</span>
            <RuiButton
              variant="text"
              color="warning"
              size="sm"
              class="ml-2 underline"
              @click="openMatchAssetMovements()"
            >
              {{ t('asset_movement_matching.banner.action') }}
            </RuiButton>
          </div>
        </li>
        <li v-if="showUnmatchedBridges">
          <div class="flex items-center">
            <span>{{ t('bridge_matching.banner.message', { count: unmatchedBridgesCount }) }}</span>
            <RuiButton
              variant="text"
              color="warning"
              size="sm"
              class="ml-2 underline"
              @click="openMatchBridgeTransactions()"
            >
              {{ t('asset_movement_matching.banner.action') }}
            </RuiButton>
          </div>
        </li>
        <li v-if="showAutoFixDuplicates">
          <div class="flex items-center">
            <span>{{ t('customized_event_duplicates.banner.auto_fix_message', { count: autoFixCount }) }}</span>
            <RuiButton
              variant="text"
              color="warning"
              size="sm"
              class="ml-2 underline"
              @click="viewDuplicates(autoFixGroupIds, DuplicateHandlingStatus.AUTO_FIX)"
            >
              {{ t('customized_event_duplicates.banner.view_action') }}
            </RuiButton>
          </div>
        </li>
        <li v-if="showManualReviewDuplicates">
          <div class="flex items-center">
            <span>{{ t('customized_event_duplicates.banner.manual_review_message', { count: manualReviewCount }) }}</span>
            <RuiButton
              variant="text"
              color="warning"
              size="sm"
              class="ml-2 underline"
              @click="viewDuplicates(manualReviewGroupIds, DuplicateHandlingStatus.MANUAL_REVIEW)"
            >
              {{ t('customized_event_duplicates.banner.view_action') }}
            </RuiButton>
          </div>
        </li>
        <li v-if="showInternalConflicts">
          <div class="flex items-center">
            <span>{{ t('internal_tx_conflicts.banner.message', { count: internalConflictsCount }) }}</span>
            <RuiButton
              variant="text"
              color="warning"
              size="sm"
              class="ml-2 underline"
              @click="openInternalTxConflicts()"
            >
              {{ t('internal_tx_conflicts.banner.action') }}
            </RuiButton>
          </div>
        </li>
        <li v-if="showUndecoded">
          <div class="flex items-center">
            <span>{{ t('transactions.events_decoding.undecoded_banner.message', { count: undecodedCount }) }}</span>
            <RuiButton
              variant="text"
              color="warning"
              size="sm"
              class="ml-2 underline"
              @click="openDecodingStatus()"
            >
              {{ t('transactions.events_decoding.undecoded_banner.action') }}
            </RuiButton>
          </div>
        </li>
      </ul>
    </RuiAlert>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
