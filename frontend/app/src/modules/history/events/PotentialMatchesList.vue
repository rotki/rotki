<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { PotentialMatchRow, UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import PotentialMatchesCards from '@/modules/history/events/PotentialMatchesCards.vue';
import PotentialMatchesEmpty from '@/modules/history/events/PotentialMatchesEmpty.vue';
import PotentialMatchSubject from '@/modules/history/events/PotentialMatchSubject.vue';
import RecommendedMatchIcon from '@/modules/history/events/RecommendedMatchIcon.vue';
import ShowInEventsButton from '@/modules/history/events/ShowInEventsButton.vue';
import { getAssetMovementsType } from '@/modules/history/management/forms/utils';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const selectedMatchIds = defineModel<number[]>('selectedMatchIds', { required: true });

const searchTimeRange = defineModel<string>('searchTimeRange', { required: true });

const onlyExpectedAssets = defineModel<boolean>('onlyExpectedAssets', { required: true });

const tolerancePercentage = defineModel<string>('tolerancePercentage', { required: true });

const { movement, matches, loading, isPinned, highlightedIdentifier, entryLabels } = defineProps<{
  movement: UnmatchedEventGroup;
  matches: PotentialMatchRow[];
  loading: boolean;
  isPinned?: boolean;
  highlightedIdentifier?: number;
  /**
   * How the unmatched entry is described in the summary table. Flows that are not asset movements
   * relabel the type badge and the location column together, so the two travel as one unit; omitting
   * it falls back to the asset-movement type and the exchange header.
   */
  entryLabels?: { type: string; locationHeader: string; matchingFor?: string };
  /** When set, the last search failed; the message is shown above the results. */
  searchError?: string;
  /** Shown when a search returns no matches, explaining why none can be found. */
  emptyExplanation?: string;
}>();

const emit = defineEmits<{
  'search': [];
  'show-in-events': [data: { identifier: number; groupIdentifier: string }];
  'show-unmatched-in-events': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { getHistoryEventSubTypeName, getHistoryEventTypeName } = useHistoryEventMappings();

const [DefineRowActions, ReuseRowActions] = createReusableTemplate<{ row: PotentialMatchRow }>();

// dialog-only: the pinned panel renders `PotentialMatchesCards` instead
const columns = computed<DataTableColumn<PotentialMatchRow>[]>(() => [
  { key: 'timestamp', label: t('common.datetime') },
  { class: 'min-w-32', key: 'eventTypeAndSubtype', label: t('asset_movement_matching.dialog.event_column') },
  { class: 'min-w-32', key: 'txRef', label: t('asset_movement_matching.dialog.transaction_column') },
  { key: 'asset', label: t('common.asset') },
  { key: 'actions', label: '' },
]);

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
  return row.entry.identifier === highlightedIdentifier ? '!bg-rui-success/15' : '';
}

const movementEntry = computed<HistoryEventEntry>(() => {
  const { entry, ...meta } = getEventEntryFromCollection(movement.events);
  return { ...entry, ...meta };
});

const usedTypeLabel = computed<string>(() => entryLabels?.type ?? getAssetMovementsType(get(movementEntry).eventSubtype));
const usedLocationHeader = computed<string>(() => entryLabels?.locationHeader ?? t('common.exchange'));

const searchControlsEl = useTemplateRef<HTMLElement>('searchControls');
const { height: searchControlsHeight } = useElementSize(searchControlsEl);

const tableMaxHeight = computed<string>(() =>
  isPinned
    ? `calc(100vh - 28.4rem - ${get(searchControlsHeight)}px)`
    : 'calc(100vh - 33rem)',
);

/** The time field's own max. */
const MAX_SEARCH_HOURS = 168;

/** Past a full 100% either side, the tolerance no longer excludes anything. */
const MAX_TOLERANCE_PERCENTAGE = 100;

/** Nothing left to widen once both criteria sit at their ceiling, so stop offering it. */
const canWiden = computed<boolean>(() =>
  Number(get(searchTimeRange)) < MAX_SEARCH_HOURS || Number(get(tolerancePercentage)) < MAX_TOLERANCE_PERCENTAGE);

/** Doubling both criteria is the cheapest useful next attempt, capped at each field's max. */
function widenSearch(): void {
  const hours = Number(get(searchTimeRange));
  if (!Number.isNaN(hours))
    set(searchTimeRange, Math.min(hours * 2, MAX_SEARCH_HOURS).toString());

  const tolerance = Number(get(tolerancePercentage));
  if (!Number.isNaN(tolerance))
    set(tolerancePercentage, Math.min(tolerance * 2, MAX_TOLERANCE_PERCENTAGE).toString());

  emit('search');
}

watchDebounced(onlyExpectedAssets, () => {
  emit('search');
}, { debounce: 200 });
</script>

<template>
  <DefineRowActions #default="{ row }">
    <div class="flex items-center justify-end gap-2">
      <RecommendedMatchIcon v-if="row.isCloseMatch" />
      <ShowInEventsButton
        @click="emit('show-in-events', { identifier: row.entry.identifier, groupIdentifier: row.entry.groupIdentifier })"
      />
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
        {{ entryLabels?.matchingFor ?? t('asset_movement_matching.dialog.matching_for') }}
      </p>
      <PotentialMatchSubject
        :entry="movementEntry"
        :type-label="usedTypeLabel"
        :location-header="usedLocationHeader"
        :is-pinned="isPinned"
        @show-in-events="emit('show-unmatched-in-events')"
      />
    </div>
    <div ref="searchControls">
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
          :label="isPinned ? t('asset_movement_matching.dialog.time_range_short') : t('asset_movement_matching.dialog.time_range_hours')"
          :class="isPinned ? 'w-28' : 'w-36'"
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
          :label="isPinned ? t('asset_movement_matching.dialog.tolerance_short') : t('asset_movement_matching.settings.amount_tolerance.label')"
          :class="isPinned ? 'w-28' : 'w-36'"
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
              class="!my-0 [&_span]:!my-0 [&_label]:!items-center"
              :class="isPinned ? '[&_span]:!text-caption' : '[&_span]:!text-sm'"
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
              :loading="loading"
              :size="isPinned ? 'sm' : 'xl'"
              :class="isPinned ? '[&>span]:!hidden !px-2.5 !h-[38px]' : 'ml-3 [&>span]:!inline'"
              @click="emit('search')"
            >
              <template #prepend>
                <RuiIcon name="lu-search" />
              </template>
              {{ t('common.actions.search') }}
            </RuiButton>
          </template>
          {{ t('common.actions.search') }}
        </RuiTooltip>
      </div>
    </div>

    <div>
      <RuiAlert
        v-if="searchError"
        type="error"
        size="sm"
        class="mb-4"
      >
        {{ searchError }}
      </RuiAlert>

      <p
        v-if="matches.length > 0"
        class="text-body-2 font-medium mb-2"
      >
        {{ t('asset_movement_matching.dialog.matching_hint') }}
      </p>

      <PotentialMatchesEmpty
        v-else-if="!loading"
        :hours="searchTimeRange"
        :tolerance="tolerancePercentage"
        :can-widen="canWiden"
        :explanation="emptyExplanation"
        @widen="widenSearch()"
      />

      <PotentialMatchesCards
        v-if="isPinned && (matches.length > 0 || loading)"
        v-model:selected-ids="selectedMatchIds"
        :matches="matches"
        :highlighted-identifier="highlightedIdentifier"
        :loading="loading"
        :max-height="tableMaxHeight"
        :empty-label="t('asset_movement_matching.dialog.no_matches_found')"
        @show-in-events="emit('show-in-events', $event)"
      />

      <ScrollableDialogContent
        v-else-if="!isPinned && (matches.length > 0 || loading)"
        :max-height="tableMaxHeight"
      >
        <RuiDataTable
          :cols="columns"
          :rows="matches"
          row-attr="identifier"
          :item-class="getRowClass"
          dense
          outlined
          hide-default-header
          :empty="{ label: t('asset_movement_matching.dialog.no_matches_found') }"
          :loading="loading"
        >
          <template #item.timestamp="{ row }">
            <DateDisplay
              :timestamp="row.entry.timestamp"
              milliseconds
            />
          </template>
          <template #item.eventTypeAndSubtype="{ row }">
            <div>{{ getHistoryEventTypeName(row.entry.eventType) }} -</div>
            <div>{{ getHistoryEventSubTypeName(row.entry.eventSubtype) }}</div>
          </template>
          <template #item.txRef="{ row }">
            <div
              v-if="'txRef' in row.entry && row.entry.txRef"
              class="flex items-center gap-1"
            >
              <LocationIcon
                horizontal
                icon
                size="1.25rem"
                :item="row.entry.location"
              />
              <HashLink
                :text="row.entry.txRef"
                type="transaction"
                :location="row.entry.location"
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
                disable-options
                :event="row.entry"
              />
            </div>
          </template>
          <template #item.actions="{ row }">
            <ReuseRowActions :row="row" />
          </template>
        </RuiDataTable>
      </ScrollableDialogContent>
    </div>
  </div>
</template>
