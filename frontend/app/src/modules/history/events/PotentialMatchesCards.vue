<script setup lang="ts">
import type { PotentialMatchRow } from '@/modules/history/events/matching/types';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import RecommendedMatchIcon from '@/modules/history/events/RecommendedMatchIcon.vue';
import ShowInEventsButton from '@/modules/history/events/ShowInEventsButton.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const selectedIds = defineModel<number[]>('selectedIds', { required: true });

const { matches, highlightedIdentifier, loading, maxHeight } = defineProps<{
  matches: PotentialMatchRow[];
  highlightedIdentifier?: number;
  loading?: boolean;
  maxHeight: string;
  emptyLabel: string;
}>();

const emit = defineEmits<{
  'show-in-events': [data: { identifier: number; groupIdentifier: string }];
}>();

const { t } = useI18n({ useScope: 'global' });

const { getHistoryEventSubTypeName, getHistoryEventTypeName } = useHistoryEventMappings();

function isSelected(row: PotentialMatchRow): boolean {
  return get(selectedIds).includes(row.entry.identifier);
}

function toggle(row: PotentialMatchRow): void {
  const identifier = row.entry.identifier;
  const ids = get(selectedIds);
  set(selectedIds, ids.includes(identifier) ? ids.filter(id => id !== identifier) : [...ids, identifier]);
}

function eventLabel(row: PotentialMatchRow): string {
  return `${getHistoryEventTypeName(row.entry.eventType)} - ${getHistoryEventSubTypeName(row.entry.eventSubtype)}`;
}
</script>

<template>
  <ScrollableDialogContent :max-height="maxHeight">
    <div
      v-if="matches.length === 0"
      class="flex items-center justify-center py-8 border border-default rounded text-body-2 text-rui-text-secondary"
      data-testid="potential-matches-empty"
    >
      <RuiProgress
        v-if="loading"
        circular
        variant="indeterminate"
        color="primary"
        size="24"
      />
      <template v-else>
        {{ emptyLabel }}
      </template>
    </div>

    <div
      v-else
      class="flex flex-col gap-2"
    >
      <div
        v-for="row in matches"
        :key="row.entry.identifier"
        class="flex flex-col gap-1 rounded border p-2 cursor-pointer transition-all"
        :class="[
          isSelected(row) ? 'border-rui-primary bg-rui-primary/5' : 'border-default hover:bg-rui-grey-50 dark:hover:bg-rui-grey-900',
          { '!bg-rui-success/15': row.entry.identifier === highlightedIdentifier },
        ]"
        :data-testid="`potential-match-${row.entry.identifier}`"
        @click="toggle(row)"
      >
        <div class="flex flex-wrap items-center gap-x-1.5 gap-y-1">
          <span class="font-medium text-rui-text">
            {{ eventLabel(row) }}
          </span>
          <RecommendedMatchIcon v-if="row.isCloseMatch" />
          <DateDisplay
            class="ml-auto text-caption text-rui-text-disabled"
            :timestamp="row.entry.timestamp"
            milliseconds
          />
        </div>

        <HistoryEventAsset
          dense
          inline
          disable-options
          :event="row.entry"
        />

        <div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-caption">
          <div
            v-if="'txRef' in row.entry && row.entry.txRef"
            class="flex items-center gap-1"
          >
            <LocationIcon
              horizontal
              icon
              size="1rem"
              :item="row.entry.location"
            />
            <HashLink
              :text="row.entry.txRef"
              type="transaction"
              :location="row.entry.location"
            />
          </div>
          <HistoryEventAccount
            v-if="row.entry.locationLabel"
            dense
            :location="row.entry.location"
            :location-label="row.entry.locationLabel"
          />

          <div
            class="ml-auto flex items-center gap-1"
            @click.stop
          >
            <ShowInEventsButton
              @click="emit('show-in-events', { groupIdentifier: row.entry.groupIdentifier, identifier: row.entry.identifier })"
            />
            <RuiButton
              size="sm"
              class="!h-[30px] !py-0 min-w-24"
              :color="isSelected(row) ? 'success' : 'primary'"
              :variant="isSelected(row) ? 'default' : 'outlined'"
              :data-testid="`potential-match-select-${row.entry.identifier}`"
              @click="toggle(row)"
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
        </div>
      </div>
    </div>
  </ScrollableDialogContent>
</template>
