<script setup lang="ts">
import type { LocationAndTxRef, PullEventPayload } from '@/modules/history/events/event-payloads';
import type { HistoryEventEntry, StandaloneEditableEvents } from '@/modules/history/events/schemas';
import { type DuplicateHandlingStatus, getHighlightClass, type HighlightType } from '@/modules/history/events/action-types';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import HistoryEventsAction from '@/modules/history/events/HistoryEventsAction.vue';
import HistoryEventsIdentifier from '@/modules/history/events/HistoryEventsIdentifier.vue';
import { useEventRedecodeStatus } from '@/modules/history/events/use-event-redecode-status';
import IgnoredInAccountingIcon from '@/modules/history/IgnoredInAccountingIcon.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

const {
  group,
  groupEvents = [],
  hideActions,
  loading,
  duplicateHandlingStatus,
  ignoredAssets,
  variant = 'row',
} = defineProps<{
  group: HistoryEventEntry;
  groupEvents?: HistoryEventEntry[];
  hideActions?: boolean;
  loading?: boolean;
  duplicateHandlingStatus?: DuplicateHandlingStatus;
  /**
   * The group's ignored-asset state. Its presence renders the indicator, and the value picks whether
   * the ignored assets are currently revealed, which is all the two former booleans could express
   * between them.
   */
  ignoredAssets?: 'hidden' | 'showing';
  /** The highlight colour. Its presence is what highlights the row. */
  highlightType?: HighlightType;
  variant?: 'row' | 'card';
}>();

const emit = defineEmits<{
  'add-event': [event: StandaloneEditableEvents];
  'toggle-ignore': [event: HistoryEventEntry];
  'toggle-show-ignored-assets': [];
  'redecode': [event: PullEventPayload];
  'redecode-with-options': [event: PullEventPayload];
  'delete-tx': [data: LocationAndTxRef];
  'delete-events': [ids: number[]];
  'fix-duplicate': [];
  'ignore-duplicate': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const showingIgnoredAssets = computed<boolean>(() => ignoredAssets === 'showing');

const isCard = computed<boolean>(() => variant === 'card');

const redecoding = useEventRedecodeStatus(() => group, () => groupEvents);
</script>

<template>
  <!-- Card Layout -->
  <div
    v-if="isCard"
    data-cy="history-event-group"
    class="pt-1 pb-2 px-3 border-b border-rui-grey-200 dark:border-rui-grey-800 bg-rui-grey-100 dark:bg-dark-elevated"
    :class="getHighlightClass(highlightType)"
  >
    <!-- Top row: Location + Identifier + Actions -->
    <div class="flex items-center justify-between gap-2 mb-0.5">
      <div class="flex items-center gap-2 min-w-0 flex-1">
        <IgnoredInAccountingIcon
          v-if="group.ignoredInAccounting"
          class="shrink-0"
        />

        <RuiTooltip
          v-if="ignoredAssets"
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

        <span
          v-if="redecoding"
          data-testid="event-redecoding"
          class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wide text-rui-primary bg-rui-primary/10 animate-pulse"
        >
          {{ t('transactions.events.redecoding') }}
        </span>
      </div>

      <HistoryEventsAction
        v-if="!hideActions"
        :event="group"
        :group-events="groupEvents"
        :loading="loading"
        :redecoding="redecoding"
        :duplicate-handling-status="duplicateHandlingStatus"
        class="shrink-0"
        @add-event="emit('add-event', $event)"
        @toggle-ignore="emit('toggle-ignore', $event)"
        @redecode="emit('redecode', $event)"
        @redecode-with-options="emit('redecode-with-options', $event)"
        @delete-tx="emit('delete-tx', $event)"
        @delete-events="emit('delete-events', $event)"
        @fix-duplicate="emit('fix-duplicate')"
        @ignore-duplicate="emit('ignore-duplicate')"
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
    :class="getHighlightClass(highlightType)"
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
      v-if="ignoredAssets"
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

      <span
        v-if="redecoding"
        data-testid="event-redecoding"
        class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wide text-rui-primary bg-rui-primary/10 animate-pulse"
      >
        {{ t('transactions.events.redecoding') }}
      </span>

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
      :group-events="groupEvents"
      :loading="loading"
      :redecoding="redecoding"
      :duplicate-handling-status="duplicateHandlingStatus"
      class="shrink-0"
      @add-event="emit('add-event', $event)"
      @toggle-ignore="emit('toggle-ignore', $event)"
      @redecode="emit('redecode', $event)"
      @redecode-with-options="emit('redecode-with-options', $event)"
      @delete-tx="emit('delete-tx', $event)"
      @delete-events="emit('delete-events', $event)"
      @fix-duplicate="emit('fix-duplicate')"
      @ignore-duplicate="emit('ignore-duplicate')"
    />
  </div>
</template>
