<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import UnmatchedMatchDisabledAlert from '@/modules/history/events/UnmatchedMatchDisabledAlert.vue';
import UnmatchedRowActions, { type UnmatchedRowActionLabels } from '@/modules/history/events/UnmatchedRowActions.vue';
import { type ColumnClassConfig, usePinnedAssetColumnClass, usePinnedColumnClass } from '@/modules/history/events/use-pinned-column-class';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

interface UnmatchedBridgeRow {
  groupIdentifier: string;
  entry: HistoryEventEntry;
  direction: 'deposit' | 'withdrawal';
  location: string;
  timestamp: number;
  original: UnmatchedBridgeTransaction;
}

const selected = defineModel<string[]>('selected', { required: true });

const {
  transactions,
  highlightedGroupIdentifier,
  ignoreLoading,
  isPinned,
  showRestore,
  loading,
  matchDisabled,
  matchMinimumTier,
} = defineProps<{
  transactions: UnmatchedBridgeTransaction[];
  highlightedGroupIdentifier?: string;
  ignoreLoading?: boolean;
  isPinned?: boolean;
  matchDisabled?: boolean;
  matchMinimumTier?: string | null;
  showRestore?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  'ignore': [transaction: UnmatchedBridgeTransaction];
  'mark-external': [transaction: UnmatchedBridgeTransaction];
  'pin': [];
  'restore': [transaction: UnmatchedBridgeTransaction];
  'select': [transaction: UnmatchedBridgeTransaction];
  'show-in-events': [transaction: UnmatchedBridgeTransaction];
}>();

const { t } = useI18n({ useScope: 'global' });

const { currentTier, premium } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);

const pinnedColumnClass = usePinnedColumnClass(() => isPinned);
const pinnedAssetColumnClass = usePinnedAssetColumnClass(() => isPinned);

function createColumns(isPinned: boolean, baseClass: ColumnClassConfig, assetClass: ColumnClassConfig): DataTableColumn<UnmatchedBridgeRow>[] {
  const columns: DataTableColumn<UnmatchedBridgeRow>[] = [
    {
      key: 'timestamp',
      label: isPinned
        ? t('bridge_matching.dialog.info_column')
        : t('common.datetime'),
      ...baseClass,
    },
  ];

  if (!isPinned) {
    columns.push(
      {
        key: 'direction',
        label: t('common.type'),
        ...baseClass,
      },
      {
        align: 'center',
        key: 'location',
        label: t('common.location'),
        ...baseClass,
      },
    );
  }

  columns.push(
    {
      key: 'asset',
      label: t('common.asset'),
      ...assetClass,
    },
    {
      key: 'actions',
      label: t('bridge_matching.dialog.manual_action'),
      ...baseClass,
    },
  );

  return columns;
}

const columns = computed<DataTableColumn<UnmatchedBridgeRow>[]>(() => createColumns(isPinned ?? false, get(pinnedColumnClass), get(pinnedAssetColumnClass)));

const rows = computed<UnmatchedBridgeRow[]>(() =>
  transactions.map((transaction) => {
    const { entry, ...meta } = getEventEntryFromCollection(transaction.events);
    const eventEntry = { ...entry, ...meta };
    return {
      direction: transaction.direction,
      entry: eventEntry,
      groupIdentifier: transaction.groupIdentifier,
      location: entry.location,
      original: transaction,
      timestamp: entry.timestamp,
    };
  }),
);

const emptyDescription = computed<string>(() =>
  showRestore
    ? t('bridge_matching.dialog.no_ignored')
    : t('bridge_matching.dialog.no_unmatched'),
);

const descriptionEl = useTemplateRef<HTMLElement>('description');
const { height: descriptionHeight } = useElementSize(descriptionEl);

const tableMaxHeight = computed<string>(() =>
  isPinned
    ? `calc(100vh - 15.4rem - ${get(descriptionHeight)}px)`
    : 'calc(100vh - 23rem)',
);

function getRowClass(row: UnmatchedBridgeRow): string {
  const classes = ['transition-all'];
  if (row.groupIdentifier === highlightedGroupIdentifier) {
    classes.push('!bg-rui-warning/15');
  }
  return classes.join(' ');
}

function actionLabels(row: UnmatchedBridgeRow): UnmatchedRowActionLabels {
  return {
    findMatch: t('asset_movement_matching.dialog.find_match'),
    ignore: t('asset_movement_matching.dialog.ignore'),
    ignoreTooltip: t('bridge_matching.dialog.ignore_tooltip'),
    markExternal: t('bridge_matching.dialog.mark_external'),
    markExternalTooltip: row.direction === 'deposit'
      ? t('bridge_matching.dialog.mark_external_tooltip')
      : t('bridge_matching.dialog.mark_external_in_tooltip'),
    restore: t('asset_movement_matching.dialog.restore'),
    restoreTooltip: t('bridge_matching.dialog.restore_tooltip'),
    showInEventsTooltip: t('asset_movement_matching.dialog.show_in_events'),
  };
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between gap-2 mb-4">
      <p
        ref="description"
        class="text-body-2 text-rui-text-secondary"
      >
        {{ showRestore ? t('bridge_matching.dialog.ignored_description') : t('bridge_matching.dialog.description') }}
      </p>
      <RuiButton
        v-if="!isPinned"
        size="sm"
        color="primary"
        variant="outlined"
        @click="emit('pin')"
      >
        <template #prepend>
          <RuiIcon
            size="18"
            name="lu-pin"
          />
        </template>
        {{ t('asset_movement_matching.actions_pin.pin_section') }}
      </RuiButton>
    </div>
    <ScrollableDialogContent :max-height="tableMaxHeight">
      <RuiDataTable
        v-model="selected"
        :cols="columns"
        :rows="rows"
        row-attr="groupIdentifier"
        :item-class="getRowClass"
        outlined
        dense
        multi-page-select
        :loading="loading"
        :empty="{ description: emptyDescription }"
      >
        <template
          v-if="matchDisabled"
          #body.prepend
        >
          <tr>
            <td :colspan="columns.length + 1">
              <UnmatchedMatchDisabledAlert
                variant="bridge"
                :premium="premium"
                :current-tier="currentTier"
                :match-minimum-tier="matchMinimumTier"
              />
            </td>
          </tr>
        </template>
        <template #item.asset="{ row }">
          <HistoryEventAsset
            :dense="isPinned"
            disable-options
            :event="row.entry"
          />
        </template>
        <template #item.direction="{ row }">
          <BadgeDisplay>
            {{ row.direction }}
          </BadgeDisplay>
        </template>
        <template #item.location="{ row }">
          <LocationDisplay
            size="24px"
            :identifier="row.location"
          />
        </template>
        <template #item.timestamp="{ row }">
          <DateDisplay
            :timestamp="row.timestamp"
            milliseconds
          />
          <div
            v-if="isPinned"
            class="flex flex-wrap items-center gap-x-1.5"
          >
            <BadgeDisplay class="!leading-6 my-1">
              {{ row.direction }}
            </BadgeDisplay>
            <LocationDisplay
              class="[&_div]:!justify-start"
              size="16px"
              :identifier="row.location"
              horizontal
            />
          </div>
        </template>
        <template #item.actions="{ row }">
          <UnmatchedRowActions
            :labels="actionLabels(row)"
            :is-pinned="isPinned"
            :show-restore="showRestore"
            :ignore-loading="ignoreLoading"
            :match-disabled="matchDisabled"
            show-mark-external
            @show-in-events="emit('show-in-events', row.original)"
            @restore="emit('restore', row.original)"
            @select="emit('select', row.original)"
            @ignore="emit('ignore', row.original)"
            @mark-external="emit('mark-external', row.original)"
          />
        </template>
      </RuiDataTable>
    </ScrollableDialogContent>
  </div>
</template>
