<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { arrayify } from '@/modules/core/common/data/array';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import UnmatchedMatchDisabledAlert from '@/modules/history/events/UnmatchedMatchDisabledAlert.vue';
import UnmatchedRowActions, { type UnmatchedRowActionLabels } from '@/modules/history/events/UnmatchedRowActions.vue';
import { type ColumnClassConfig, usePinnedAssetColumnClass, usePinnedColumnClass } from '@/modules/history/events/use-pinned-column-class';
import { getBridgeCounterpartAddress, getBridgeCounterpartChain, isCounterpartUnqueryable, useUntrackedBridgeCounterpart } from '@/modules/history/events/use-untracked-bridge-counterpart';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

interface UnmatchedBridgeRow {
  /** Row key: the leg event identifier, since a group can carry several bridge legs. */
  id: string;
  groupIdentifier: string;
  entry: HistoryEventEntry;
  direction: 'deposit' | 'withdrawal';
  location: string;
  timestamp: number;
  original: UnmatchedBridgeTransaction;
  counterpartAddress?: string;
  untrackedCounterpart: boolean;
  canCreateCounterpart: boolean;
  unqueryableCounterpart: boolean;
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
  'create-counterpart': [transaction: UnmatchedBridgeTransaction];
  'ignore': [transaction: UnmatchedBridgeTransaction];
  'mark-external': [transaction: UnmatchedBridgeTransaction];
  'pin': [];
  'restore': [transaction: UnmatchedBridgeTransaction];
  'select': [transaction: UnmatchedBridgeTransaction];
  'show-in-events': [transaction: UnmatchedBridgeTransaction];
}>();

const { t } = useI18n({ useScope: 'global' });

const { currentTier, premium } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);
const { isCounterpartUntracked } = useUntrackedBridgeCounterpart();

const pinnedColumnClass = usePinnedColumnClass(() => isPinned);
const pinnedAssetColumnClass = usePinnedAssetColumnClass(() => isPinned);

const [DefineUntrackedBadge, ReuseUntrackedBadge] = createReusableTemplate<{ row: UnmatchedBridgeRow }>();

function untrackedBadgeLabel(row: UnmatchedBridgeRow): string {
  return row.direction === 'deposit'
    ? t('bridge_matching.dialog.untracked_destination')
    : t('bridge_matching.dialog.untracked_source');
}

function untrackedBadgeTooltip(row: UnmatchedBridgeRow): string {
  const address = row.counterpartAddress ?? '';
  return row.direction === 'deposit'
    ? t('bridge_matching.dialog.untracked_destination_tooltip', { address })
    : t('bridge_matching.dialog.untracked_source_tooltip', { address });
}

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
    // Show the leg's own event: the row's collection can hold several events and the
    // first one is not necessarily the leg this row acts on.
    const { entry, ...meta } = arrayify(transaction.events).find(event => event.entry.identifier === transaction.identifier)
      ?? getEventEntryFromCollection(transaction.events);
    const eventEntry = { ...entry, ...meta };
    return {
      id: transaction.identifier.toString(),
      canCreateCounterpart: !showRestore && getBridgeCounterpartChain(transaction) !== undefined,
      counterpartAddress: getBridgeCounterpartAddress(transaction),
      direction: transaction.direction,
      entry: eventEntry,
      groupIdentifier: transaction.groupIdentifier,
      location: entry.location,
      original: transaction,
      timestamp: entry.timestamp,
      unqueryableCounterpart: !showRestore && isCounterpartUnqueryable(transaction),
      untrackedCounterpart: !showRestore && isCounterpartUntracked(transaction),
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
    createCounterpart: t('bridge_matching.dialog.create_counterpart'),
    createCounterpartTooltip: row.direction === 'deposit'
      ? t('bridge_matching.dialog.create_counterpart_tooltip')
      : t('bridge_matching.dialog.create_counterpart_in_tooltip'),
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
  <DefineUntrackedBadge #default="{ row }">
    <RuiTooltip
      :open-delay="200"
      :popper="{ placement: 'top' }"
      tooltip-class="max-w-80"
    >
      <template #activator>
        <RuiChip
          size="sm"
          color="warning"
          class="!py-0"
        >
          <span class="flex items-center gap-1">
            <RuiIcon
              size="14"
              name="lu-triangle-alert"
            />
            {{ untrackedBadgeLabel(row) }}
          </span>
        </RuiChip>
      </template>
      {{ untrackedBadgeTooltip(row) }}
    </RuiTooltip>
  </DefineUntrackedBadge>

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
        row-attr="id"
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
          <div class="flex flex-col items-start gap-1">
            <BadgeDisplay>
              {{ row.direction }}
            </BadgeDisplay>
            <ReuseUntrackedBadge
              v-if="row.untrackedCounterpart"
              :row="row"
            />
          </div>
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
            <ReuseUntrackedBadge
              v-if="row.untrackedCounterpart"
              :row="row"
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
            :emphasize-mark-external="row.untrackedCounterpart && !row.unqueryableCounterpart"
            :show-create-counterpart="row.canCreateCounterpart"
            :emphasize-create-counterpart="row.unqueryableCounterpart"
            @show-in-events="emit('show-in-events', row.original)"
            @restore="emit('restore', row.original)"
            @select="emit('select', row.original)"
            @ignore="emit('ignore', row.original)"
            @mark-external="emit('mark-external', row.original)"
            @create-counterpart="emit('create-counterpart', row.original)"
          />
        </template>
      </RuiDataTable>
    </ScrollableDialogContent>
  </div>
</template>
