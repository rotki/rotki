<script setup lang="ts">
import type { DuplicateHandlingStatus } from '@/composables/history/events/types';
import type { LocationAndTxRef, PullEventPayload } from '@/types/history/events';
import type { HistoryEventEntry, StandaloneEditableEvents } from '@/types/history/events/schemas';
import DateDisplay from '@/components/display/DateDisplay.vue';
import HistoryEventAccount from '@/components/history/events/HistoryEventAccount.vue';
import HistoryEventsAction from '@/components/history/events/HistoryEventsAction.vue';
import HistoryEventsIdentifier from '@/components/history/events/HistoryEventsIdentifier.vue';
import IgnoredInAccountingIcon from '@/components/history/IgnoredInAccountingIcon.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';

const props = withDefaults(defineProps<{
  group: HistoryEventEntry;
  groupEvents?: HistoryEventEntry[];
  hideActions?: boolean;
  loading?: boolean;
  duplicateHandlingStatus?: DuplicateHandlingStatus;
  hasHiddenIgnoredAssets?: boolean;
  showingIgnoredAssets?: boolean;
  variant?: 'row' | 'card';
}>(), {
  groupEvents: () => [],
  variant: 'row',
});

const emit = defineEmits<{
  'add-event': [event: StandaloneEditableEvents];
  'toggle-ignore': [event: HistoryEventEntry];
  'toggle-show-ignored-assets': [];
  'redecode': [event: PullEventPayload];
  'redecode-with-options': [event: PullEventPayload];
  'delete-tx': [data: LocationAndTxRef];
  'fix-duplicate': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { hasHiddenIgnoredAssets, showingIgnoredAssets } = toRefs(props);

// Show indicator if group has hidden ignored assets OR is currently showing them
const showIgnoredAssetsIndicator = computed<boolean>(() =>
  get(hasHiddenIgnoredAssets) || get(showingIgnoredAssets),
);

const { group } = toRefs(props);

const isCard = computed<boolean>(() => props.variant === 'card');
</script>

<template>
  <!-- Card Layout -->
  <div
    v-if="isCard"
    data-cy="history-event-group"
    class="pt-1 pb-2 px-3 border-b border-rui-grey-200 dark:border-rui-grey-800 bg-rui-grey-100 dark:bg-dark-elevated"
  >
    <!-- Top row: Location + Identifier + Actions -->
    <div class="flex items-center justify-between gap-2 mb-0.5">
      <div class="flex items-center gap-2 min-w-0 flex-1">
        <IgnoredInAccountingIcon
          v-if="group.ignoredInAccounting"
          class="shrink-0"
        />

        <RuiTooltip
          v-if="showIgnoredAssetsIndicator"
          :popper="{ placement: 'top', scroll: false, resize: false }"
          :open-delay="400"
          tooltip-class="max-w-60"
        >
          <template #activator>
            <button
              type="button"
              class="p-0.5 rounded hover:bg-rui-grey-300 dark:hover:bg-rui-grey-700 transition-colors shrink-0"
              @click="emit('toggle-show-ignored-assets')"
            >
              <RuiIcon
                :name="showingIgnoredAssets ? 'lu-eye' : 'lu-eye-off'"
                class="text-rui-warning shrink-0"
                size="16"
              />
            </button>
          </template>
          {{
            showingIgnoredAssets
              ? t('transactions.events.showing_ignored_assets')
              : t('transactions.events.hidden_ignored_assets_warning')
          }}
        </RuiTooltip>

        <LocationIcon
          icon
          :item="group.location"
          size="18px"
          class="shrink-0"
        />

        <HistoryEventsIdentifier
          :event="group"
          :group-events="groupEvents"
          class="min-w-0 flex-1"
        />
      </div>

      <HistoryEventsAction
        v-if="!hideActions"
        :event="group"
        :loading="loading"
        :duplicate-handling-status="duplicateHandlingStatus"
        class="shrink-0"
        @add-event="emit('add-event', $event)"
        @toggle-ignore="emit('toggle-ignore', $event)"
        @redecode="emit('redecode', $event)"
        @redecode-with-options="emit('redecode-with-options', $event)"
        @delete-tx="emit('delete-tx', $event)"
        @fix-duplicate="emit('fix-duplicate')"
      />
    </div>

    <!-- Bottom row: Account + Timestamp -->
    <div class="flex items-center justify-between gap-2">
      <HistoryEventAccount
        v-if="group.locationLabel"
        :location="group.location"
        :location-label="group.locationLabel"
        class="text-sm text-rui-text-secondary min-w-0"
      />

      <DateDisplay
        :timestamp="group.timestamp"
        milliseconds
        class="text-xs text-rui-text-secondary shrink-0"
      />
    </div>
  </div>

  <!-- Row Layout -->
  <div
    v-else
    data-cy="history-event-group"
    class="h-12 flex items-center gap-2.5 border-b border-default !border-t-rui-grey-400 dark:!border-t-rui-grey-600 pl-2 pr-4 bg-white dark:bg-dark-elevated contain-content"
  >
    <IgnoredInAccountingIcon
      v-if="group.ignoredInAccounting"
      class="shrink-0"
    />
    <div
      v-else
      class=" shrink-0"
    />

    <RuiTooltip
      v-if="showIgnoredAssetsIndicator"
      :popper="{ placement: 'top', scroll: false, resize: false }"
      :open-delay="400"
      tooltip-class="max-w-60"
    >
      <template #activator>
        <button
          type="button"
          class="p-0.5 rounded hover:bg-rui-grey-300 dark:hover:bg-rui-grey-700 transition-colors"
          @click="emit('toggle-show-ignored-assets')"
        >
          <RuiIcon
            :name="showingIgnoredAssets ? 'lu-eye' : 'lu-eye-off'"
            class="text-rui-warning shrink-0"
            size="16"
          />
        </button>
      </template>
      {{
        showingIgnoredAssets
          ? t('transactions.events.showing_ignored_assets')
          : t('transactions.events.hidden_ignored_assets_warning')
      }}
    </RuiTooltip>

    <LocationIcon
      icon
      :item="group.location"
      size="20px"
      class="shrink-0"
    />

    <div class="flex items-center gap-2.5 min-w-0 flex-1">
      <HistoryEventsIdentifier
        :event="group"
        :group-events="groupEvents"
        class="min-w-0"
      />

      <template v-if="group.locationLabel">
        <!-- eslint-disable-next-line @intlify/vue-i18n/no-raw-text -->
        <span class="text-[10px] text-rui-text-secondary shrink-0">●</span>
        <HistoryEventAccount
          :location="group.location"
          :location-label="group.locationLabel"
          class="text-sm min-w-0"
        />
      </template>
    </div>

    <DateDisplay
      :timestamp="group.timestamp"
      milliseconds
      class="text-right shrink-0 text-sm"
    />

    <HistoryEventsAction
      v-if="!hideActions"
      :event="group"
      :loading="loading"
      :duplicate-handling-status="duplicateHandlingStatus"
      class="shrink-0"
      @add-event="emit('add-event', $event)"
      @toggle-ignore="emit('toggle-ignore', $event)"
      @redecode="emit('redecode', $event)"
      @redecode-with-options="emit('redecode-with-options', $event)"
      @delete-tx="emit('delete-tx', $event)"
      @fix-duplicate="emit('fix-duplicate')"
    />
  </div>
</template>
