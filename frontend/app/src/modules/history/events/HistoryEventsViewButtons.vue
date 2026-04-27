<script setup lang="ts">
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import { DIALOG_TYPES, type DialogShowOptions } from '@/modules/history/events/dialog-types';
import HistoryEventsIssueCheckButton from '@/modules/history/events/HistoryEventsIssueCheckButton.vue';
import { useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { useInternalTxConflicts } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflicts';
import HistoryRefreshButton from '@/modules/history/refresh/HistoryRefreshButton.vue';

const showAlerts = defineModel<boolean>('showAlerts', { default: false });

const { processing } = defineProps<{
  processing: boolean;
  loading: boolean;
  includeEvmEvents: boolean;
}>();

const emit = defineEmits<{
  'refresh': [payload?: HistoryRefreshEventData];
  'show:dialog': [options: DialogShowOptions];
}>();

const { t } = useI18n({ useScope: 'global' });

type IssueCheckType = 'unmatched' | 'duplicates';

const menuOpen = ref<boolean>(false);
const checkingType = ref<IssueCheckType>();
const noIssuesFeedback = ref<IssueCheckType>();

const { refreshUnmatchedAssetMovements, unmatchedCount, ignoredCount } = useUnmatchedAssetMovements();
const { fetchCustomizedEventDuplicates, totalCount: duplicatesCount } = useCustomizedEventDuplicates();
const { issueCount: internalConflictsCount } = useInternalTxConflicts();

const { start: startFeedbackTimeout, stop: stopFeedbackTimeout } = useTimeoutFn(() => {
  set(noIssuesFeedback, undefined);
}, 2000, { immediate: false });

function showNoIssuesFeedback(type: IssueCheckType): void {
  stopFeedbackTimeout();
  set(noIssuesFeedback, type);
  startFeedbackTimeout();
}

async function checkUnmatched(): Promise<void> {
  set(checkingType, 'unmatched');
  try {
    await refreshUnmatchedAssetMovements();
    if (get(unmatchedCount) > 0 || get(ignoredCount) > 0) {
      set(menuOpen, false);
      emit('show:dialog', { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS });
    }
    else {
      showNoIssuesFeedback('unmatched');
    }
  }
  finally {
    set(checkingType, undefined);
  }
}

async function checkDuplicates(): Promise<void> {
  set(checkingType, 'duplicates');
  try {
    await fetchCustomizedEventDuplicates();
    if (get(duplicatesCount) > 0) {
      set(menuOpen, false);
      emit('show:dialog', { type: DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES });
    }
    else {
      showNoIssuesFeedback('duplicates');
    }
  }
  finally {
    set(checkingType, undefined);
  }
}

function checkInternalConflicts(): void {
  set(menuOpen, false);
  emit('show:dialog', { type: DIALOG_TYPES.INTERNAL_TX_CONFLICTS });
}
</script>

<template>
  <HistoryEventsIssueCheckButton
    v-model:show-alerts="showAlerts"
    @show:dialog="emit('show:dialog', $event)"
  />

  <HistoryRefreshButton
    :processing="processing"
    @refresh="emit('refresh', $event)"
  />

  <RuiButton
    color="primary"
    size="lg"
    class="[&>span]:!hidden lg:[&>span]:!inline"
    data-cy="history-events__add"
    @click="emit('show:dialog', { type: DIALOG_TYPES.EVENT_FORM, data: { type: 'add', nextSequenceId: '0' } })"
  >
    <template #prepend>
      <RuiIcon name="lu-plus" />
    </template>
    {{ t('transactions.actions.add_event') }}
  </RuiButton>

  <RuiMenu
    v-model="menuOpen"
    :popper="{ placement: 'bottom-end' }"
    menu-class="max-w-[24rem]"
    close-on-content-click
  >
    <template #activator="{ attrs }">
      <RuiBadge
        :model-value="loading"
        color="primary"
        dot
        placement="top"
        offset-y="12"
        offset-x="-12"
      >
        <RuiButton
          variant="text"
          icon
          size="lg"
          v-bind="attrs"
        >
          <RuiIcon name="lu-ellipsis-vertical" />
        </RuiButton>
      </RuiBadge>
    </template>

    <template v-if="includeEvmEvents">
      <RuiButton
        variant="list"
        @click="emit('show:dialog', { type: DIALOG_TYPES.DECODING_STATUS })"
      >
        <template #prepend>
          <RuiBadge
            :model-value="loading"
            color="primary"
            dot
            placement="top"
            offset-y="4"
            offset-x="-4"
          >
            <RuiIcon name="lu-scroll-text" />
          </RuiBadge>
        </template>

        {{ t('transactions.events_decoding.title') }}
      </RuiButton>
    </template>

    <RuiButton
      variant="list"
      data-cy="history-events__add_by_tx_hash"
      :disabled="loading"
      @click="emit('show:dialog', { type: DIALOG_TYPES.ADD_TRANSACTION })"
    >
      <template #prepend>
        <RuiIcon name="lu-plus" />
      </template>
      {{ t('transactions.dialog.add_tx') }}
    </RuiButton>

    <RuiButton
      variant="list"
      data-cy="history-events__repulling-transactions"
      :disabled="loading"
      @click="emit('show:dialog', { type: DIALOG_TYPES.REPULLING_TRANSACTION })"
    >
      <template #prepend>
        <RuiIcon name="lu-clock-arrow-up" />
      </template>
      {{ t('transactions.repulling.action') }}
    </RuiButton>

    <RuiDivider class="my-1" />

    <RuiButton
      variant="list"
      :disabled="processing || !!checkingType"
      :loading="checkingType === 'unmatched'"
      :color="noIssuesFeedback === 'unmatched' ? 'success' : undefined"
      @click.stop="checkUnmatched()"
    >
      <template #prepend>
        <RuiIcon :name="noIssuesFeedback === 'unmatched' ? 'lu-circle-check' : 'lu-git-compare-arrows'" />
      </template>
      {{ noIssuesFeedback === 'unmatched' ? t('transactions.alerts.no_issues_found') : t('transactions.alerts.check_unmatched_movements') }}
    </RuiButton>

    <RuiButton
      variant="list"
      :disabled="processing || !!checkingType"
      :loading="checkingType === 'duplicates'"
      :color="noIssuesFeedback === 'duplicates' ? 'success' : undefined"
      @click.stop="checkDuplicates()"
    >
      <template #prepend>
        <RuiIcon :name="noIssuesFeedback === 'duplicates' ? 'lu-circle-check' : 'lu-copy'" />
      </template>
      {{ noIssuesFeedback === 'duplicates' ? t('transactions.alerts.no_issues_found') : t('transactions.alerts.check_duplicate_events') }}
    </RuiButton>

    <RuiButton
      variant="list"
      :disabled="processing || !!checkingType"
      @click.stop="checkInternalConflicts()"
    >
      <template #prepend>
        <RuiBadge
          :model-value="internalConflictsCount > 0"
          color="warning"
          dot
          placement="top"
          offset-y="4"
          offset-x="-4"
        >
          <RuiIcon name="lu-git-merge" />
        </RuiBadge>
      </template>
      {{ t('transactions.alerts.check_internal_conflicts') }}
    </RuiButton>
  </RuiMenu>
</template>
