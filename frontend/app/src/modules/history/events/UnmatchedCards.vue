<script setup lang="ts" generic="TItem">
import type { UnmatchedPresentationEmits, UnmatchedPresentationProps, UnmatchedRow } from '@/modules/history/events/unmatched-row';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import { UNMATCHED_LAYOUTS } from '@/modules/history/events/unmatched-actions';
import UnmatchedActions from '@/modules/history/events/UnmatchedActions.vue';
import UnmatchedCardList from '@/modules/history/events/UnmatchedCardList.vue';
import UnmatchedFiatHint from '@/modules/history/events/UnmatchedFiatHint.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const selected = defineModel<string[]>('selected', { required: true });

const { highlightedGroupIdentifier } = defineProps<UnmatchedPresentationProps<TItem>>();

const emit = defineEmits<UnmatchedPresentationEmits<TItem>>();

defineSlots<{
  alert?: () => unknown;
}>();

function rowKey(row: UnmatchedRow<TItem>): string {
  return row.id;
}

function isHighlighted(row: UnmatchedRow<TItem>): boolean {
  return row.groupIdentifier === highlightedGroupIdentifier;
}

function isUntracked(row: UnmatchedRow<TItem>): boolean {
  return row.untracked;
}
</script>

<template>
  <UnmatchedCardList
    v-model:selected="selected"
    :items="rows"
    :row-key="rowKey"
    :highlighted="isHighlighted"
    :accented="isUntracked"
    :empty-description="emptyDescription"
    :failure="failure"
    :loading="loading"
    @retry="emit('retry')"
  >
    <template
      v-if="$slots.alert"
      #alert
    >
      <slot name="alert" />
    </template>

    <template #header="{ item }">
      <div class="flex flex-wrap items-center gap-x-1.5 gap-y-1">
        <BadgeDisplay class="normal-case!">
          {{ item.typeLabel }}
        </BadgeDisplay>
        <RuiChip
          v-if="item.resolvedLabel"
          size="sm"
          color="info"
          class="py-0!"
          data-testid="unmatched-row-resolved"
        >
          {{ item.resolvedLabel }}
        </RuiChip>
        <LocationDisplay
          size="16px"
          :identifier="item.location"
          horizontal
          dense
        />
        <UnmatchedFiatHint
          v-if="item.isFiat"
          dense
        />
        <DateDisplay
          class="ml-auto text-caption text-rui-text-disabled"
          :timestamp="item.timestamp"
          milliseconds
        />
      </div>
    </template>

    <template #warning="{ item }">
      <div
        v-if="item.untracked"
        class="flex items-start gap-1.5 rounded-sm px-2 py-1 text-caption bg-rui-warning/10 text-rui-warning"
        data-testid="unmatched-card-untracked-reason"
      >
        <RuiIcon
          size="14"
          name="lu-triangle-alert"
          class="shrink-0 mt-0.5"
        />
        <div class="flex flex-col items-start gap-0.5 min-w-0">
          <i18n-t
            scope="global"
            keypath="asset_movement_matching.dialog.untracked_reason"
            tag="span"
          >
            <template #label>
              <strong>{{ item.untrackedLabel }}</strong>
            </template>
          </i18n-t>
          <HashLink
            v-if="item.untrackedAddress"
            class="[&_span]:text-caption!"
            :text="item.untrackedAddress"
          />
        </div>
      </div>
    </template>

    <template #asset="{ item }">
      <HistoryEventAsset
        dense
        inline
        disable-options
        :event="item.entry"
      />
    </template>

    <template #actions="{ item }">
      <UnmatchedActions
        :spec="specFor(item)"
        :layout="UNMATCHED_LAYOUTS.CARD"
        :ignore-loading="ignoreLoading"
        @action="emit('action', { action: $event, item: item.original })"
      />
    </template>
  </UnmatchedCardList>
</template>
