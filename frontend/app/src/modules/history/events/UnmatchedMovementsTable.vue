<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import type { UnmatchedMovementRow } from '@/modules/history/events/use-unmatched-movement-rows';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import { UNMATCHED_LAYOUTS, type UnmatchedActionPayload, type UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import UnmatchedActions from '@/modules/history/events/UnmatchedActions.vue';
import UnmatchedUntrackedBadge from '@/modules/history/events/UnmatchedUntrackedBadge.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

// The dialog presentation of unmatched movements. Layout only - see UnmatchedMovementsList.
const selected = defineModel<string[]>('selected', { required: true });

const { highlightedGroupIdentifier } = defineProps<{
  rows: UnmatchedMovementRow[];
  specFor: (row: UnmatchedMovementRow) => UnmatchedRowActionSpec;
  emptyDescription: string;
  maxHeight: string;
  highlightedGroupIdentifier?: string;
  ignoreLoading?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  action: [payload: UnmatchedActionPayload<UnmatchedAssetMovement>];
}>();

defineSlots<{
  alert?: () => unknown;
}>();

const { t } = useI18n({ useScope: 'global' });

const columns = computed<DataTableColumn<UnmatchedMovementRow>[]>(() => [
  {
    key: 'timestamp',
    label: t('common.datetime'),
  },
  {
    key: 'eventSubtype',
    label: t('common.type'),
  },
  {
    align: 'center',
    key: 'location',
    label: t('common.exchange'),
  },
  {
    key: 'asset',
    label: t('common.asset'),
  },
  {
    key: 'actions',
    label: t('asset_movement_matching.dialog.manual_action'),
  },
]);

function getRowClass(row: UnmatchedMovementRow): string {
  const classes = ['transition-all'];
  if (row.groupIdentifier === highlightedGroupIdentifier) {
    classes.push('!bg-rui-warning/15');
  }
  return classes.join(' ');
}
</script>

<template>
  <ScrollableDialogContent :max-height="maxHeight">
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
        v-if="$slots.alert"
        #body.prepend
      >
        <tr>
          <td :colspan="columns.length + 1">
            <slot name="alert" />
          </td>
        </tr>
      </template>
      <template #item.asset="{ row }">
        <div class="flex items-center gap-2">
          <HistoryEventAsset
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
      <template #item.eventSubtype="{ row }">
        <div class="flex flex-col items-start gap-1">
          <BadgeDisplay>
            {{ row.typeLabel }}
          </BadgeDisplay>
          <template v-if="row.untrackedDestination">
            <UnmatchedUntrackedBadge
              :label="row.untrackedLabel"
              :tooltip="row.untrackedTooltip"
            />
            <HashLink
              v-if="row.destinationAddress"
              class="[&_span]:!text-caption"
              :text="row.destinationAddress"
            />
          </template>
          <RuiChip
            v-if="row.resolvedAsExternal"
            size="sm"
            color="info"
            class="!py-0"
            data-testid="unmatched-row-resolved"
          >
            {{ row.resolvedLabel }}
          </RuiChip>
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
      </template>
      <template #item.actions="{ row }">
        <UnmatchedActions
          :spec="specFor(row)"
          :layout="UNMATCHED_LAYOUTS.ROW"
          :ignore-loading="ignoreLoading"
          @action="emit('action', { action: $event, item: row.original })"
        />
      </template>
    </RuiDataTable>
  </ScrollableDialogContent>
</template>
