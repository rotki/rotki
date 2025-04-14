<script setup lang="ts">
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events';
import LazyLoader from '@/components/helper/LazyLoader.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HistoryEventsListItem from '@/components/history/events/HistoryEventsListItem.vue';
import HistoryEventsListItemAction from '@/components/history/events/HistoryEventsListItemAction.vue';
import HistoryEventType from '@/components/history/events/HistoryEventType.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { HistoryEventEntryType } from '@rotki/common';

interface HistoryEventsListTableProps {
  events: HistoryEventEntry[];
  eventGroup: HistoryEventEntry;
  loading?: boolean;
  total?: number;
  highlightedIdentifiers?: string[];
}

const props = withDefaults(defineProps<HistoryEventsListTableProps>(), {
  loading: false,
  total: 0,
});

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: { canDelete: boolean; item: HistoryEventEntry }];
  'show:missing-rule-action': [data: HistoryEventEditData];
}>();

const { t } = useI18n();

const isCompact = ref(true);
const isInitialRender = ref(true);

const { getChain } = useSupportedChains();
const { assetSymbol } = useAssetInfoRetrieval();

const allowCompactView = computed(() => props.eventGroup.entryType === HistoryEventEntryType.SWAP_EVENT);
const usedIsCompact = logicAnd(allowCompactView, isCompact);

function getSwapEventRank(eventSubtype: string): number {
  if (eventSubtype === 'spend') {
    return -1;
  }
  if (eventSubtype === 'receive') {
    return 1;
  }
  return 0;
}

const formattedEvents = computed(() => {
  if (!get(usedIsCompact)) {
    return props.events;
  }

  return props.events.filter(item => item.eventSubtype !== 'fee').sort((a, b) => getSwapEventRank(a.eventSubtype) - getSwapEventRank(b.eventSubtype));
});

const compactNotes = computed(() => {
  if (!get(usedIsCompact))
    return undefined;

  const events = get(formattedEvents);
  const outAsset = events.find(item => item.eventSubtype === 'spend');
  const inAsset = events.find(item => item.eventSubtype === 'receive');

  if (!outAsset || !inAsset) {
    return undefined;
  }

  const outAssetNote = `${outAsset.amount} ${get(assetSymbol(outAsset.asset))}`;
  const inAssetNote = `${inAsset.amount} ${get(assetSymbol(inAsset.asset))}`;

  let notes = `Swap ${outAssetNote} for ${inAssetNote}`;

  const feeAsset = props.events.find(item => item.eventSubtype === 'fee');
  if (feeAsset) {
    const feeAssetNote = `${feeAsset.amount} ${get(assetSymbol(feeAsset.asset))}`;
    notes = `${notes} with fee ${feeAssetNote}`;
  }

  return notes;
});

// Add this watch to set isInitialRender to false after the first change
watch(isCompact, () => {
  if (get(isInitialRender)) {
    set(isInitialRender, false);
  }
});

const [DefineTemplate, ReuseTemplate] = createReusableTemplate<{
  item: HistoryEventEntry;
  index: number;
}>();
</script>

<template>
  <DefineTemplate #default="{ item, index }">
    <HistoryEventsListItem
      class="flex-1"
      :item="item"
      :index="index"
      :events="events"
      :event-group="eventGroup"
      :compact="usedIsCompact"
      :is-last="index === events.length - 1"
      :is-highlighted="highlightedIdentifiers?.includes(item.identifier.toString())"
      @edit-event="emit('edit-event', $event)"
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', $event)"
    />
  </DefineTemplate>
  <div>
    <template v-if="total > 0">
      <template v-if="!allowCompactView">
        <ReuseTemplate
          v-for="(item, index) in events"
          :key="item.identifier"
          :item="item"
          :index="index"
        />
      </template>
      <template v-else>
        <TransitionGroup
          tag="div"
          name="list"
          class="relative"
          :class="{
            'grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 items-start gap-3 gap-y-1': usedIsCompact,
            'flex flex-col': !usedIsCompact,
            'transition-wrapper': !isInitialRender,
          }"
        >
          <LazyLoader
            v-if="usedIsCompact"
            class="pt-4 pb-0 lg:py-4.5"
          >
            <HistoryEventType
              icon="lu-arrow-right-left"
              :event="formattedEvents[0]"
              highlight
              :chain="getChain(formattedEvents[0].location)"
            />
          </LazyLoader>
          <template
            v-for="(item, index) in formattedEvents"
            :key="item.identifier"
          >
            <div
              class="flex flex-col md:flex-row"
              :data-subtype="item.eventSubtype"
            >
              <ReuseTemplate
                :item="item"
                :index="index"
              />
              <LazyLoader
                v-if="index === 0 && usedIsCompact"
                class="py-0 md:py-6 text-rui-grey-400 dark:text-rui-grey-600"
              >
                <RuiIcon
                  name="lu-chevron-right"
                  size="24"
                  class="rotate-90 md:rotate-0"
                />
              </LazyLoader>
            </div>
          </template>
          <template v-if="usedIsCompact">
            <LazyLoader
              v-if="compactNotes"
              class="py-2 lg:pt-4 lg:pb-4"
              min-height="70"
            >
              <HistoryEventNote
                class="md:col-span-2 lg:col-span-1"
                :notes="compactNotes"
                :amount="events.map(item => item.amount)"
              />
            </LazyLoader>
            <LazyLoader
              class="py-0 lg:py-4"
              min-height="40"
            >
              <HistoryEventsListItemAction
                :item="formattedEvents[0]"
                :index="0"
                :events="events"
                @edit-event="emit('edit-event', $event)"
                @delete-event="emit('delete-event', $event)"
                @show:missing-rule-action="emit('show:missing-rule-action', $event)"
              />
            </LazyLoader>
          </template>
        </TransitionGroup>
        <LazyLoader
          class="pb-2"
          min-height="36"
        >
          <RuiButton
            variant="text"
            color="primary"
            @click="isCompact = !isCompact"
          >
            <template #prepend>
              <RuiIcon
                name="lu-chevron-down"
                size="16"
                class="transition-all"
                :class="{ 'rotate-180': !usedIsCompact }"
              />
            </template>
            {{ usedIsCompact ? t('transactions.events.view.view_detail') : t('transactions.events.view.compact_view') }}
          </RuiButton>
        </LazyLoader>
      </template>
    </template>

    <template v-else>
      <div v-if="loading">
        {{ t('transactions.events.loading') }}
      </div>
      <div v-else>
        {{ t('transactions.events.no_data') }}
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.transition-wrapper {
  .list-move,
  .list-enter-active,
  .list-leave-active {
    @apply transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)];
  }

  .list-enter-from,
  .list-leave-to {
    @apply opacity-0;
  }

  .list-leave-active {
    @apply absolute w-full;

    &[data-subtype="fee"] {
      @apply transition-none !important;
    }
  }
}
</style>
