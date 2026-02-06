<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { UnmatchedAssetMovement } from '@/composables/history/events/use-unmatched-asset-movements';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import DateDisplay from '@/components/display/DateDisplay.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { type ColumnClassConfig, usePinnedAssetColumnClass, usePinnedColumnClass } from '@/composables/history/events/use-pinned-column-class';
import { getEventEntryFromCollection } from '@/utils/history/events';

interface UnmatchedMovementRow {
  groupIdentifier: string;
  entry: HistoryEventEntry;
  eventType: string;
  isFiat: boolean;
  location: string;
  timestamp: number;
  original: UnmatchedAssetMovement;
}

const selected = defineModel<string[]>('selected', { required: true });

const props = defineProps<{
  movements: UnmatchedAssetMovement[];
  highlightedGroupIdentifier?: string;
  ignoreLoading?: boolean;
  isPinned?: boolean;
  showRestore?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  'ignore': [movement: UnmatchedAssetMovement];
  'pin': [];
  'restore': [movement: UnmatchedAssetMovement];
  'select': [movement: UnmatchedAssetMovement];
  'show-in-events': [movement: UnmatchedAssetMovement];
}>();

const { t } = useI18n({ useScope: 'global' });

const { isPinned } = toRefs(props);

const pinnedColumnClass = usePinnedColumnClass(isPinned);
const pinnedAssetColumnClass = usePinnedAssetColumnClass(isPinned);

function createColumns(isPinned: boolean, baseClass: ColumnClassConfig, assetClass: ColumnClassConfig): DataTableColumn<UnmatchedMovementRow>[] {
  const columns: DataTableColumn<UnmatchedMovementRow>[] = [
    {
      key: 'timestamp',
      label: isPinned
        ? t('asset_movement_matching.dialog.info_column')
        : t('common.datetime'),
      ...baseClass,
    },
  ];

  if (!isPinned) {
    columns.push(
      {
        key: 'eventType',
        label: t('common.type'),
        ...baseClass,
      },
      {
        align: 'center',
        key: 'location',
        label: t('common.exchange'),
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
      label: t('asset_movement_matching.dialog.manual_action'),
      ...baseClass,
    },
  );

  return columns;
}

const columns = computed<DataTableColumn<UnmatchedMovementRow>[]>(() => createColumns(props.isPinned ?? false, get(pinnedColumnClass), get(pinnedAssetColumnClass)));

const rows = computed<UnmatchedMovementRow[]>(() =>
  props.movements.map((movement) => {
    const { entry, ...meta } = getEventEntryFromCollection(movement.events);
    const eventEntry = { ...entry, ...meta };
    return {
      entry: eventEntry,
      eventType: entry.eventType,
      groupIdentifier: movement.groupIdentifier,
      isFiat: movement.isFiat,
      location: entry.location,
      original: movement,
      timestamp: entry.timestamp,
    };
  }),
);

const emptyDescription = computed<string>(() =>
  props.showRestore
    ? t('asset_movement_matching.dialog.no_ignored')
    : t('asset_movement_matching.dialog.no_unmatched'),
);

function getRowClass(row: UnmatchedMovementRow): string {
  const classes = ['transition-all'];
  if (row.groupIdentifier === props.highlightedGroupIdentifier) {
    classes.push('!bg-rui-warning/15');
  }
  return classes.join(' ');
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between gap-2 mb-4">
      <p class="text-body-2 text-rui-text-secondary">
        {{ showRestore ? t('asset_movement_matching.dialog.ignored_description') : t('asset_movement_matching.dialog.description') }}
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
      :class="!isPinned ? 'max-h-[calc(100vh-23rem)]' : 'h-[calc(100vh-17.9rem)] !max-h-none'"
      class="table-inside-dialog"
      :empty="{ description: emptyDescription }"
    >
      <template #item.asset="{ row }">
        <div class="flex items-center gap-2">
          <HistoryEventAsset
            :dense="isPinned"
            disable-options
            :event="row.entry"
          />
          <RuiTooltip
            v-if="row.isFiat"
            :open-delay="400"
            :popper="{ placement: 'top' }"
            tooltip-class="max-w-80"
          >
            <template #activator>
              <RuiChip
                size="sm"
                color="warning"
              >
                {{ t('asset_movement_matching.fiat_hint.label') }}
              </RuiChip>
            </template>
            {{ t('asset_movement_matching.fiat_hint.tooltip') }}
          </RuiTooltip>
        </div>
      </template>
      <template #item.eventType="{ row }">
        <BadgeDisplay>
          {{ row.eventType }}
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
        <template v-if="isPinned">
          <BadgeDisplay class="!leading-6 my-1">
            {{ row.eventType }}
          </BadgeDisplay>
          <LocationDisplay
            class="[&_div]:!justify-start"
            size="16px"
            :identifier="row.location"
            horizontal
          />
        </template>
      </template>
      <template #item.actions="{ row }">
        <div class="flex items-center gap-2">
          <RuiTooltip
            :open-delay="400"
            :popper="{ placement: 'top' }"
          >
            <template #activator>
              <RuiButton
                size="sm"
                variant="outlined"
                icon
                color="primary"
                class="!px-2 h-[30px]"
                @click="emit('show-in-events', row.original)"
              >
                <RuiIcon
                  size="16"
                  name="lu-external-link"
                />
              </RuiButton>
            </template>
            {{ t('asset_movement_matching.dialog.show_in_events') }}
          </RuiTooltip>
          <template v-if="showRestore">
            <RuiTooltip
              :open-delay="400"
              :popper="{ placement: 'top' }"
            >
              <template #activator>
                <RuiButton
                  size="sm"
                  color="primary"
                  :loading="ignoreLoading"
                  @click="emit('restore', row.original)"
                >
                  {{ t('asset_movement_matching.dialog.restore') }}
                </RuiButton>
              </template>
              {{ t('asset_movement_matching.dialog.restore_tooltip') }}
            </RuiTooltip>
          </template>
          <div
            v-else
            class="flex"
            :class="isPinned ? 'flex-col gap-1' : 'gap-2'"
          >
            <RuiButton
              size="sm"
              color="primary"
              :class="{ '!py-0.5': isPinned }"
              @click="emit('select', row.original)"
            >
              {{ t('asset_movement_matching.dialog.find_match') }}
            </RuiButton>
            <RuiTooltip
              :open-delay="400"
              :popper="{ placement: 'top' }"
            >
              <template #activator>
                <RuiButton
                  size="sm"
                  variant="outlined"
                  :class="{ '!py-0.5': isPinned }"
                  :loading="ignoreLoading"
                  @click="emit('ignore', row.original)"
                >
                  {{ t('asset_movement_matching.dialog.ignore') }}
                </RuiButton>
              </template>
              {{ t('asset_movement_matching.dialog.ignore_tooltip') }}
            </RuiTooltip>
          </div>
        </div>
      </template>
    </RuiDataTable>
  </div>
</template>
