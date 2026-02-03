<script setup lang="ts">
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import { DIALOG_TYPES, type DialogShowOptions } from '@/components/history/events/dialog-types';
import { useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import { useUnmatchedAssetMovements } from '@/composables/history/events/use-unmatched-asset-movements';
import HistoryRefreshButton from '@/modules/history/refresh/HistoryRefreshButton.vue';
import { useStatusStore } from '@/store/status';
import { Section, Status } from '@/types/status';

const showAlerts = defineModel<boolean>('showAlerts', { default: false });
const manualIssueCheck = defineModel<boolean>('manualIssueCheck', { default: false });

const props = defineProps<{
  processing: boolean;
  loading: boolean;
  includeEvmEvents: boolean;
  mainPage?: boolean;
  sectionLoading?: boolean;
}>();

const emit = defineEmits<{
  'refresh': [payload?: HistoryRefreshEventData];
  'show:dialog': [options: DialogShowOptions];
}>();

const { mainPage, sectionLoading } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });
const { getStatus } = useStatusStore();

const { autoMatchLoading, refreshUnmatchedAssetMovements, unmatchedCount } = useUnmatchedAssetMovements();
const { fetchCustomizedEventDuplicates, totalCount: duplicatesCount } = useCustomizedEventDuplicates();

const totalIssuesCount = computed<number>(() => get(unmatchedCount) + get(duplicatesCount));
const hasIssues = computed<boolean>(() => !get(autoMatchLoading) && get(totalIssuesCount) > 0);
const showAlertsButton = computed<boolean>(() =>
  get(mainPage) && (get(manualIssueCheck) || (!get(sectionLoading) && getStatus(Section.HISTORY) === Status.LOADED)) && get(hasIssues),
);

const checkingIssues = ref<boolean>(false);
const noIssuesFound = ref<boolean>(false);

const { start: startNoIssuesTimeout, stop: stopNoIssuesTimeout } = useTimeoutFn(() => {
  set(noIssuesFound, false);
}, 2000, { immediate: false });

const hasOnlyUnmatchedMovements = computed<boolean>(() => get(unmatchedCount) > 0 && get(duplicatesCount) === 0);

function toggleAlerts(): void {
  if (get(hasOnlyUnmatchedMovements)) {
    emit('show:dialog', { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS });
  }
  else {
    set(showAlerts, !get(showAlerts));
  }
}

function openAlertsIfNeeded(): void {
  if (!get(showAlertsButton))
    return;

  if (get(hasOnlyUnmatchedMovements)) {
    emit('show:dialog', { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS });
  }
  else {
    set(showAlerts, true);
  }
}

function showNoIssuesFeedback(): void {
  stopNoIssuesTimeout();
  set(noIssuesFound, true);
  startNoIssuesTimeout();
}

async function checkIssues(): Promise<void> {
  set(manualIssueCheck, true);
  set(checkingIssues, true);
  try {
    await Promise.all([
      refreshUnmatchedAssetMovements(),
      fetchCustomizedEventDuplicates(),
    ]);
    openAlertsIfNeeded();
    if (!get(hasIssues))
      showNoIssuesFeedback();
  }
  finally {
    set(checkingIssues, false);
  }
}

async function checkUnmatched(): Promise<void> {
  set(manualIssueCheck, true);
  await refreshUnmatchedAssetMovements();
  openAlertsIfNeeded();
  if (!get(hasIssues))
    showNoIssuesFeedback();
}

async function checkDuplicates(): Promise<void> {
  set(manualIssueCheck, true);
  await fetchCustomizedEventDuplicates();
  openAlertsIfNeeded();
  if (!get(hasIssues))
    showNoIssuesFeedback();
}
</script>

<template>
  <RuiButtonGroup
    variant="outlined"
    :color="showAlertsButton ? 'warning' : noIssuesFound ? 'success' : 'primary'"
    class="h-9"
  >
    <RuiBadge
      v-if="showAlertsButton"
      :model-value="totalIssuesCount > 0"
      :text="totalIssuesCount.toString()"
      color="warning"
      placement="top"
      offset-y="4"
      offset-x="-4"
    >
      <RuiButton
        variant="outlined"
        color="warning"
        class="rounded-r-none !outline-none border-r border-rui-warning/[0.5]"
        @click="toggleAlerts()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-triangle-alert"
            size="18"
          />
        </template>
        {{ t('transactions.alerts.button') }}
        <template #append>
          <RuiIcon
            name="lu-chevron-down"
            size="16"
            class="transition-transform duration-200"
            :class="{ 'rotate-180': showAlerts }"
          />
        </template>
      </RuiButton>
    </RuiBadge>

    <RuiButton
      v-else
      variant="outlined"
      :color="noIssuesFound ? 'success' : 'primary'"
      :loading="checkingIssues"
      class="rounded-r-none !outline-none border-r"
      :class="noIssuesFound ? 'border-rui-success/[0.5]' : 'border-rui-primary/[0.5]'"
      @click="checkIssues()"
    >
      <template #prepend>
        <RuiIcon
          :name="noIssuesFound ? 'lu-circle-check' : 'lu-search-check'"
          size="18"
        />
      </template>
      {{ noIssuesFound ? t('transactions.alerts.no_issues_found') : t('transactions.alerts.check_issues') }}
    </RuiButton>

    <RuiMenu
      :popper="{ placement: 'bottom-end' }"
      menu-class="max-w-[24rem]"
      close-on-content-click
      wrapper-class="h-full"
    >
      <template #activator="{ attrs }">
        <RuiButton
          variant="outlined"
          :color="showAlertsButton ? 'warning' : noIssuesFound ? 'success' : 'primary'"
          class="rounded-l-none !outline-none px-3 h-9"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-chevrons-up-down"
            size="16"
          />
        </RuiButton>
      </template>

      <div class="py-2">
        <RuiButton
          variant="list"
          @click="checkUnmatched()"
        >
          <template #prepend>
            <RuiIcon name="lu-git-compare-arrows" />
          </template>
          {{ showAlertsButton ? t('transactions.alerts.refresh_unmatched_movements') : t('transactions.alerts.check_unmatched_movements') }}
        </RuiButton>

        <RuiButton
          variant="list"
          @click="checkDuplicates()"
        >
          <template #prepend>
            <RuiIcon name="lu-copy" />
          </template>
          {{ showAlertsButton ? t('transactions.alerts.refresh_duplicate_events') : t('transactions.alerts.check_duplicate_events') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </RuiButtonGroup>

  <HistoryRefreshButton
    :processing="processing"
    @refresh="emit('refresh', $event)"
  />

  <RuiButton
    color="primary"
    data-cy="history-events__add"
    @click="emit('show:dialog', { type: DIALOG_TYPES.EVENT_FORM, data: { type: 'add', nextSequenceId: '0' } })"
  >
    <template #prepend>
      <RuiIcon
        name="lu-plus"
        size="18"
      />
    </template>
    {{ t('transactions.actions.add_event') }}
  </RuiButton>

  <RuiMenu
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
          :icon="true"
          size="sm"
          class="!p-2"
          v-bind="attrs"
        >
          <RuiIcon name="lu-ellipsis-vertical" />
        </RuiButton>
      </RuiBadge>
    </template>

    <div class="py-2">
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
    </div>
  </RuiMenu>
</template>
