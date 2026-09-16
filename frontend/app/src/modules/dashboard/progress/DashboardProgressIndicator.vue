<script setup lang="ts">
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import IdleQuerySection from '@/modules/dashboard/progress/components/IdleQuerySection.vue';
import { useUnifiedProgress } from '@/modules/dashboard/progress/use-unified-progress';
import { isMajorOrMinorUpdate } from './is-major-or-minor-update';

const { t } = useI18n({ useScope: 'global' });

const justUpdated = ref<boolean>(false);

const { appVersion } = storeToRefs(useMainStore());

const {
  dismissalThresholdMs,
  hasUndecodedTransactions,
  isNeverQueried,
  lastQueriedDisplay,
  lastQueriedTimestamp,
  longQuery,
  navigateToHistory,
  processing,
  queryStatus,
  showIdleMessage,
  transactionStatusSummary,
} = useUnifiedProgress();

const dismissedRecently = computed<boolean>(() => Date.now() - get(queryStatus).lastDismissedTs < get(dismissalThresholdMs));

/**
 * The banner says what state history was left in, never how work in flight is going: that is the
 * task dock's. So it steps aside while history is being queried, rather than reporting stale state.
 */
const showSection = logicAnd(
  useRefWithDebounce(logicAnd(showIdleMessage, logicNot(processing)), 300),
  logicNot(dismissedRecently),
);

function dismiss(): void {
  set(queryStatus, {
    ...get(queryStatus),
    lastDismissedTs: Date.now(),
    lastUsedVersion: get(appVersion),
  });
}

onMounted(async () => {
  const currentVersion = get(appVersion);
  const lastVersion = get(queryStatus, 'lastUsedVersion');

  // If it's a major or minor update, reset the dismissal
  if (isMajorOrMinorUpdate(currentVersion, lastVersion)) {
    set(queryStatus, {
      lastDismissedTs: 0,
      lastUsedVersion: currentVersion,
    });
    set(justUpdated, true);
    return;
  }

  if (currentVersion === lastVersion) {
    return;
  }

  // Update version but keep the dismissal for patch updates
  set(queryStatus, {
    lastDismissedTs: get(queryStatus, 'lastDismissedTs') || 0,
    lastUsedVersion: currentVersion,
  });
});
</script>

<template>
  <Transition
    enter-active-class="transition-all duration-100 ease-out"
    enter-from-class="-translate-y-full opacity-0"
    enter-to-class="translate-y-0 opacity-100"
    leave-active-class="transition-all duration-100 ease-in"
    leave-from-class="translate-y-0 opacity-100"
    leave-to-class="-translate-y-full opacity-0"
  >
    <div
      v-if="showSection"
      class="w-full px-4 py-2 border-b border-default bg-white dark:bg-dark-elevated text-sm text-rui-text-secondary flex items-center justify-between gap-4"
    >
      <div class="flex items-center gap-2">
        <IdleQuerySection
          :just-updated="justUpdated"
          :is-never-queried="isNeverQueried"
          :long-query="longQuery"
          :has-undecoded-txs="hasUndecodedTransactions"
          :transaction-status="transactionStatusSummary"
          :last-queried-display="lastQueriedDisplay"
          :last-queried-timestamp="lastQueriedTimestamp"
        />
      </div>

      <div class="flex gap-2">
        <RuiButton
          variant="text"
          size="sm"
          color="primary"
          @click="navigateToHistory()"
        >
          {{ t("dashboard.history_query_indicator.go_to_history_events") }}
        </RuiButton>
        <RuiButton
          variant="text"
          icon
          size="sm"
          @click="dismiss()"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </div>
    </div>
  </Transition>
</template>
