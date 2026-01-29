<script setup lang="ts">
import type { DuplicateHandlingStatus } from '@/composables/history/events/use-history-events-filters';
import type { LocationAndTxRef, PullEventPayload } from '@/types/history/events';
import type { HistoryEventEntry, StandaloneEditableEvents } from '@/types/history/events/schemas';
import DateDisplay from '@/components/display/DateDisplay.vue';
import HistoryEventAccount from '@/components/history/events/HistoryEventAccount.vue';
import HistoryEventsAction from '@/components/history/events/HistoryEventsAction.vue';
import HistoryEventsIdentifier from '@/components/history/events/HistoryEventsIdentifier.vue';
import IgnoredInAccountingIcon from '@/components/history/IgnoredInAccountingIcon.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';

const props = defineProps<{
  group: HistoryEventEntry;
  hideActions?: boolean;
  loading?: boolean;
  duplicateHandlingStatus?: DuplicateHandlingStatus;
  hasHiddenIgnoredAssets?: boolean;
  showingIgnoredAssets?: boolean;
}>();

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
</script>

<template>
  <div class="h-12 flex items-center gap-2.5 border-b border-default !border-t-rui-grey-400 dark:!border-t-rui-grey-600 pl-1 pr-4 bg-rui-grey-100 dark:bg-dark-elevated contain-content">
    <!-- Ignored indicator -->
    <IgnoredInAccountingIcon
      v-if="group.ignoredInAccounting"
      class="shrink-0"
    />
    <div
      v-else
      class="w-4 shrink-0"
    />

    <!-- Hidden ignored assets toggle -->
    <RuiTooltip
      v-if="showIgnoredAssetsIndicator"
      :popper="{ placement: 'top', scroll: false, resize: false }"
      :open-delay="400"
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

    <!-- Location icon -->
    <LocationIcon
      icon
      :item="group.location"
      size="20px"
      class="shrink-0"
    />

    <!-- Event identifier + Account grouped together -->
    <div class="flex items-center gap-2.5 min-w-0 flex-1">
      <HistoryEventsIdentifier
        :event="group"
        truncate
        class="min-w-0"
      />

      <!-- Account -->
      <template v-if="group.locationLabel">
        <!-- eslint-disable-next-line @intlify/vue-i18n/no-raw-text -->
        <span class="text-[10px] text-rui-text-secondary shrink-0">●</span>
        <HistoryEventAccount
          :location="group.location"
          :location-label="group.locationLabel"
          class="text-sm shrink-0"
        />
      </template>
    </div>

    <!-- Timestamp -->
    <DateDisplay
      :timestamp="group.timestamp"
      milliseconds
      class="w-40 text-right shrink-0 text-sm"
    />

    <!-- Actions -->
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
