<script setup lang="ts">
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import { DIALOG_TYPES, type DialogShowOptions } from '@/components/history/events/dialog-types';
import { useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import { useUnmatchedAssetMovements } from '@/composables/history/events/use-unmatched-asset-movements';
import HistoryRefreshButton from '@/modules/history/refresh/HistoryRefreshButton.vue';
import { useStatusStore } from '@/store/status';
import { Section, Status } from '@/types/status';

const showAlerts = defineModel<boolean>('showAlerts', { default: false });

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

const { autoMatchLoading, unmatchedCount } = useUnmatchedAssetMovements();
const { totalCount: duplicatesCount } = useCustomizedEventDuplicates();

const totalIssuesCount = computed<number>(() => get(unmatchedCount) + get(duplicatesCount));
const hasIssues = computed<boolean>(() => !get(autoMatchLoading) && get(totalIssuesCount) > 0);
const showAlertsButton = computed<boolean>(() =>
  get(mainPage) === true && !get(sectionLoading) && getStatus(Section.HISTORY) === Status.LOADED && get(hasIssues),
);

function toggleAlerts(): void {
  set(showAlerts, !get(showAlerts));
}
</script>

<template>
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
      @click="toggleAlerts()"
    >
      <template #prepend>
        <RuiIcon name="lu-triangle-alert" />
      </template>
      {{ t('transactions.alerts.title') }}
    </RuiButton>
  </RuiBadge>

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
      <RuiIcon name="lu-plus" />
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

      <RuiButton
        variant="list"
        :disabled="processing"
        @click="emit('show:dialog', { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS })"
      >
        <template #prepend>
          <RuiIcon name="lu-git-compare-arrows" />
        </template>
        {{ t('asset_movement_matching.dialog.check_unmatched') }}
      </RuiButton>

      <RuiButton
        variant="list"
        :disabled="processing"
        @click="emit('show:dialog', { type: DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES })"
      >
        <template #prepend>
          <RuiIcon name="lu-copy-check" />
        </template>
        {{ t('customized_event_duplicates.dialog.check_duplicates') }}
      </RuiButton>
    </div>
  </RuiMenu>
</template>
