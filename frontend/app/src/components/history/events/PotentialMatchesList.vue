<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type {
  PotentialMatchRow,
  UnmatchedAssetMovement,
} from '@/composables/history/events/use-unmatched-asset-movements';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import SimpleTable from '@/components/common/SimpleTable.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import HistoryEventAccount from '@/components/history/events/HistoryEventAccount.vue';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { type ColumnClassConfig, usePinnedAssetColumnClass, usePinnedColumnClass, usePinnedSimpleTableClass } from '@/composables/history/events/use-pinned-column-class';
import HashLink from '@/modules/common/links/HashLink.vue';
import { getAssetMovementsType } from '@/modules/history/management/forms/utils';
import { getEventEntryFromCollection } from '@/utils/history/events';

const selectedMatchIds = defineModel<number[]>('selectedMatchIds', { required: true });

const searchTimeRange = defineModel<string>('searchTimeRange', { required: true });

const onlyExpectedAssets = defineModel<boolean>('onlyExpectedAssets', { required: true });

const tolerancePercentage = defineModel<string>('tolerancePercentage', { required: true });

const props = defineProps<{
  movement: UnmatchedAssetMovement;
  matches: PotentialMatchRow[];
  loading: boolean;
  isPinned?: boolean;
  highlightedIdentifier?: number;
}>();

const emit = defineEmits<{
  'search': [];
  'show-in-events': [data: { identifier: number; groupIdentifier: string }];
  'show-unmatched-in-events': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { isPinned } = toRefs(props);

const { getHistoryEventSubTypeName, getHistoryEventTypeName } = useHistoryEventMappings();

const [DefineRowActions, ReuseRowActions] = createReusableTemplate<{ row: PotentialMatchRow }>();

const pinnedColumnClass = usePinnedColumnClass(isPinned);
const pinnedAssetColumnClass = usePinnedAssetColumnClass(isPinned);
const pinnedSimpleTableClass = usePinnedSimpleTableClass(isPinned);

function createColumns(isPinned: boolean, baseClass: ColumnClassConfig, assetClass: ColumnClassConfig): DataTableColumn<PotentialMatchRow>[] {
  const columns: DataTableColumn<PotentialMatchRow>[] = [
    {
      key: 'timestamp',
      label: isPinned
        ? t('asset_movement_matching.dialog.info_column')
        : t('common.datetime'),
      ...baseClass,
    },
  ];

  if (!isPinned) {
    columns.push({
      key: 'eventTypeAndSubtype',
      label: `${t('transactions.events.form.event_type.label')} -\n${t('transactions.events.form.event_subtype.label')}`,
      class: `whitespace-pre-line min-w-32 ${baseClass.class ?? ''}`.trim(),
      cellClass: baseClass.cellClass ?? '',
    });
  }

  columns.push(
    {
      key: 'txRef',
      label: `${t('common.tx_hash')} -\n${t('common.account')}`,
      class: `whitespace-pre-line min-w-32 ${baseClass.class ?? ''}`.trim(),
      cellClass: baseClass.cellClass ?? '',
    },
    {
      key: 'asset',
      label: t('common.asset'),
      ...assetClass,
    },
  );

  if (!isPinned) {
    columns.push({ key: 'actions', label: '', ...baseClass });
  }

  return columns;
}

const columns = computed<DataTableColumn<PotentialMatchRow>[]>(() => createColumns(props.isPinned ?? false, get(pinnedColumnClass), get(pinnedAssetColumnClass)));

function isSelected(row: PotentialMatchRow): boolean {
  return get(selectedMatchIds).includes(row.entry.identifier);
}

function toggleSelection(row: PotentialMatchRow): void {
  const ids = get(selectedMatchIds);
  const identifier = row.entry.identifier;
  if (ids.includes(identifier)) {
    set(selectedMatchIds, ids.filter(id => id !== identifier));
  }
  else {
    set(selectedMatchIds, [...ids, identifier]);
  }
}

function getRowClass(row: PotentialMatchRow): string {
  return row.entry.identifier === props.highlightedIdentifier ? '!bg-rui-success/15' : '';
}

const movementEntry = computed<HistoryEventEntry>(() => {
  const { entry, ...meta } = getEventEntryFromCollection(props.movement.events);
  return { ...entry, ...meta };
});

const tableClass = computed<string>(() => {
  if (props.isPinned)
    return '!overflow-auto !max-h-none !h-[calc(100vh-33rem)]';
  return 'table-inside-dialog !max-h-[calc(100vh-33rem)]';
});

watchDebounced(onlyExpectedAssets, () => {
  emit('search');
}, { debounce: 200 });
</script>

<template>
  <DefineRowActions #default="{ row }">
    <div
      class="flex items-center gap-2"
      :class="isPinned ? 'justify-start' : 'justify-end'"
    >
      <RuiTooltip
        v-if="row.isCloseMatch && !isPinned"
        :open-delay="200"
      >
        <template #activator>
          <RuiIcon
            name="lu-thumbs-up"
            size="16"
            color="success"
          />
        </template>
        {{ t('asset_movement_matching.dialog.recommended') }}
      </RuiTooltip>
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
            @click="emit('show-in-events', { identifier: row.entry.identifier, groupIdentifier: row.entry.groupIdentifier })"
          >
            <RuiIcon
              size="16"
              name="lu-external-link"
            />
          </RuiButton>
        </template>
        {{ t('asset_movement_matching.dialog.show_in_events') }}
      </RuiTooltip>
      <RuiButton
        size="sm"
        :color="isSelected(row) ? 'success' : 'primary'"
        :variant="isSelected(row) ? 'default' : 'outlined'"
        class="min-w-24"
        @click="toggleSelection(row)"
      >
        <template
          v-if="isSelected(row)"
          #prepend
        >
          <RuiIcon
            name="lu-check"
            size="12"
          />
        </template>
        {{ isSelected(row)
          ? t('asset_movement_matching.dialog.selected')
          : t('asset_movement_matching.dialog.select')
        }}
      </RuiButton>
    </div>
  </DefineRowActions>

  <div class="flex flex-col gap-4">
    <div>
      <p class="text-body-2 font-medium mb-2">
        {{ t('asset_movement_matching.dialog.matching_for') }}
      </p>
      <SimpleTable
        :class="pinnedSimpleTableClass"
      >
        <thead>
          <tr>
            <th>{{ t('common.datetime') }}</th>
            <th>{{ t('common.type') }}</th>
            <th
              v-if="!isPinned"
              class="!text-center"
            >
              {{ t('common.exchange') }}
            </th>
            <th>{{ t('common.asset') }}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr :class="{ 'bg-rui-warning/15': isPinned }">
            <td>
              <DateDisplay
                :timestamp="movementEntry.timestamp"
                milliseconds
              />
            </td>
            <td>
              <BadgeDisplay :class="{ '!leading-6 mb-1': isPinned }">
                {{ getAssetMovementsType(movementEntry.eventSubtype) }}
              </BadgeDisplay>
              <LocationDisplay
                v-if="isPinned"
                class="[&_div]:!justify-start"
                size="16px"
                :identifier="movementEntry.location"
                horizontal
              />
            </td>
            <td
              v-if="!isPinned"
              class="text-center"
            >
              <LocationDisplay
                horizontal
                :identifier="movementEntry.location"
              />
            </td>
            <td>
              <HistoryEventAsset
                :dense="isPinned"
                disable-options
                :event="movementEntry"
              />
            </td>
            <td class="text-right">
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
                    @click="emit('show-unmatched-in-events')"
                  >
                    <RuiIcon
                      size="16"
                      name="lu-external-link"
                    />
                  </RuiButton>
                </template>
                {{ t('asset_movement_matching.dialog.show_in_events') }}
              </RuiTooltip>
            </td>
          </tr>
        </tbody>
      </SimpleTable>
    </div>
    <div>
      <div class="text-body-2 font-medium mb-4">
        {{ t('asset_movement_matching.dialog.search_description') }}
      </div>
      <div
        class="flex items-center flex-wrap"
        :class="isPinned ? 'gap-2' : 'gap-4'"
      >
        <RuiTextField
          v-model="searchTimeRange"
          type="number"
          min="1"
          color="primary"
          hide-details
          max="168"
          :label="t('asset_movement_matching.dialog.time_range_hours')"
          class="w-36"
          variant="outlined"
          dense
        />
        <AmountInput
          v-model="tolerancePercentage"
          type="number"
          step="0.001"
          variant="outlined"
          hide-details
          dense
          :label="t('asset_movement_matching.settings.amount_tolerance.label')"
          class="w-36"
        />
        <RuiTooltip
          :popper="{ placement: 'top' }"
          tooltip-class="max-w-80"
        >
          <template #activator>
            <RuiCheckbox
              v-model="onlyExpectedAssets"
              color="primary"
              hide-details
              size="sm"
              class="!my-0 [&_span]:!text-sm [&_span]:!my-0 [&_label]:!items-center"
              :class="{ 'whitespace-break-spaces': isPinned }"
            >
              {{ t('asset_movement_matching.dialog.only_expected_assets') }}
            </RuiCheckbox>
          </template>
          {{ t('asset_movement_matching.dialog.only_expected_assets_hint') }}
        </RuiTooltip>
        <RuiTooltip
          :open-delay="200"
          :disabled="!isPinned"
        >
          <template #activator>
            <RuiButton
              class="!h-10 ml-3"
              :loading="loading"
              :size="isPinned ? 'sm' : undefined"
              :class="isPinned ? '[&>span]:!hidden !px-2.5' : '[&>span]:!inline'"
              @click="emit('search')"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-search"
                  size="18"
                />
              </template>
              {{ t('common.actions.search') }}
            </RuiButton>
          </template>
          {{ t('common.actions.search') }}
        </RuiTooltip>
      </div>
    </div>

    <div>
      <p class="text-body-2 font-medium mb-2">
        {{ t('asset_movement_matching.dialog.matching_hint') }}
      </p>

      <RuiDataTable
        :cols="columns"
        :rows="matches"
        row-attr="identifier"
        :class="tableClass"
        :item-class="getRowClass"
        dense
        outlined
        :empty="{ label: t('asset_movement_matching.dialog.no_matches_found') }"
        :loading="loading"
      >
        <template #item.timestamp="{ row }">
          <div class="flex flex-col gap-1">
            <DateDisplay
              :timestamp="row.entry.timestamp"
              milliseconds
            />
            <div
              v-if="isPinned"
              class="font-bold"
            >
              {{ getHistoryEventTypeName(row.entry.eventType) }} -
              {{ getHistoryEventSubTypeName(row.entry.eventSubtype) }}
            </div>
          </div>
        </template>
        <template #item.eventTypeAndSubtype="{ row }">
          <div>{{ getHistoryEventTypeName(row.entry.eventType) }} -</div>
          <div>{{ getHistoryEventSubTypeName(row.entry.eventSubtype) }}</div>
        </template>
        <template #item.txRef="{ row }">
          <div
            v-if="'txRef' in row.entry && row.entry.txRef"
            class="flex items-center"
            :class="isPinned ? 'gap-2' : 'gap-1'"
          >
            <LocationIcon
              horizontal
              icon
              size="1.25rem"
              :item="row.entry.location"
              :class="{ '!text-xs': isPinned }"
            />
            <HashLink
              :text="row.entry.txRef"
              type="transaction"
              :location="row.entry.location"
              :class="{ '!text-[10px]': isPinned }"
            />
          </div>
          <div>
            <span v-if="!row.entry.locationLabel">-</span>
            <HistoryEventAccount
              v-else
              :location="row.entry.location"
              :location-label="row.entry.locationLabel"
            />
          </div>
        </template>
        <template #item.asset="{ row }">
          <div class="flex items-center gap-2">
            <HistoryEventAsset
              :dense="isPinned"
              :class="{ '-mt-2 -mb-1': isPinned }"
              disable-options
              :event="row.entry"
            />
            <RuiTooltip
              v-if="row.isCloseMatch && isPinned"
              :open-delay="200"
            >
              <template #activator>
                <RuiIcon
                  name="lu-thumbs-up"
                  size="16"
                  color="success"
                />
              </template>
              {{ t('asset_movement_matching.dialog.recommended') }}
            </RuiTooltip>
          </div>
          <ReuseRowActions
            v-if="isPinned"
            :row="row"
          />
        </template>
        <template #item.actions="{ row }">
          <ReuseRowActions :row="row" />
        </template>
      </RuiDataTable>
    </div>
  </div>
</template>
