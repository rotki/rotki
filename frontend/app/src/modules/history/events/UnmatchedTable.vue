<script setup lang="ts" generic="TRow extends UnmatchedRow<unknown>">
import type { DataTableColumn } from '@rotki/ui-library';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import TableFailureDescription from '@/modules/core/table/TableFailureDescription.vue';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import { HISTORY_DIALOG_MAX_HEIGHT } from '@/modules/history/events/dialog-layout';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import { UNMATCHED_LAYOUTS } from '@/modules/history/events/unmatched-actions';
import { type UnmatchedPresentationEmits, type UnmatchedRow, type UnmatchedTableProps, UnmatchedVariant } from '@/modules/history/events/unmatched-row';
import UnmatchedActions from '@/modules/history/events/UnmatchedActions.vue';
import UnmatchedFiatHint from '@/modules/history/events/UnmatchedFiatHint.vue';
import UnmatchedUntrackedBadge from '@/modules/history/events/UnmatchedUntrackedBadge.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const selected = defineModel<string[]>('selected', { required: true });

const { highlightedGroupIdentifier, variant } = defineProps<UnmatchedTableProps<TRow>>();

const emit = defineEmits<UnmatchedPresentationEmits<TRow['original']>>();

defineSlots<{
  alert?: () => unknown;
}>();

const { t } = useI18n({ useScope: 'global' });

const isBridge = computed<boolean>(() => variant === UnmatchedVariant.BRIDGE);

const columns = computed<DataTableColumn<TRow>[]>(() => [
  {
    key: 'timestamp',
    label: t('common.datetime'),
  },
  {
    key: 'type',
    label: t('common.type'),
  },
  {
    align: 'center',
    key: 'location',
    label: get(isBridge) ? t('common.location') : t('common.exchange'),
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

function getRowClass(row: TRow): string {
  const classes = ['transition-all'];
  if (row.groupIdentifier === highlightedGroupIdentifier) {
    classes.push('bg-rui-warning/15!');
  }
  return classes.join(' ');
}
</script>

<template>
  <ScrollableDialogContent :max-height="HISTORY_DIALOG_MAX_HEIGHT">
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
      :empty="failure ? { label: failure.title } : { description: emptyDescription }"
    >
      <template
        v-if="failure"
        #empty-description
      >
        <TableFailureDescription
          :message="failure.message"
          @retry="emit('retry')"
        />
      </template>
      <template
        v-if="$slots.alert || (failure && rows.length > 0)"
        #body.prepend
      >
        <tr>
          <td :colspan="columns.length + 1">
            <FailureStrip
              v-if="failure && rows.length > 0"
              in-table
              :title="failure.title"
              :failure="failure.message"
              @retry="emit('retry')"
            />
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
          <UnmatchedFiatHint v-if="row.isFiat" />
        </div>
      </template>
      <template #item.type="{ row }">
        <div class="flex flex-col items-start gap-1">
          <BadgeDisplay class="normal-case!">
            {{ row.typeLabel }}
          </BadgeDisplay>
          <template v-if="row.untracked">
            <UnmatchedUntrackedBadge
              :label="row.untrackedLabel"
              :tooltip="row.untrackedTooltip"
            />
            <HashLink
              v-if="row.untrackedAddress"
              class="[&_span]:text-caption!"
              :text="row.untrackedAddress"
            />
          </template>
          <RuiChip
            v-if="row.resolvedLabel"
            size="sm"
            color="info"
            class="py-0!"
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
