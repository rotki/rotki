<script setup lang="ts">
import { useSyncProgress } from '../composables/use-sync-progress';
import { SyncPhase } from '../types';
import SyncProgressStats from './SyncProgressStats.vue';

defineProps<{
  expanded: boolean;
  canDismiss: boolean;
}>();

const emit = defineEmits<{
  toggle: [];
  dismiss: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  phase,
  overallProgress,
  totalChains,
  completedChains,
  totalLocations,
  completedLocations,
  decoding,
  protocolCache,
} = useSyncProgress();

const isComplete = computed<boolean>(() => get(phase) === SyncPhase.COMPLETE);
const isSyncing = computed<boolean>(() => get(phase) === SyncPhase.SYNCING);
const showSpinner = computed<boolean>(() => get(isSyncing) && get(overallProgress) < 100);

const statusIcon = computed<string>(() => {
  if (get(isComplete))
    return 'lu-circle-check';
  return 'lu-loader-circle';
});

const statusColor = computed<string>(() => {
  if (get(isComplete))
    return 'text-rui-success';
  return 'text-rui-primary';
});

const title = computed<string>(() => {
  if (get(isComplete))
    return t('sync_progress.complete');
  return t('sync_progress.title');
});

const decodingTotal = computed<number>(() => get(decoding).length);
const decodingCompleted = computed<number>(() => get(decoding).filter(d => d.processed >= d.total).length);

const chainsStats = computed(() => ({
  completed: get(completedChains),
  hasData: get(totalChains) > 0,
  isComplete: get(completedChains) === get(totalChains) && get(totalChains) > 0,
  total: get(totalChains),
}));

const locationsStats = computed(() => ({
  completed: get(completedLocations),
  hasData: get(totalLocations) > 0,
  isComplete: get(completedLocations) === get(totalLocations) && get(totalLocations) > 0,
  total: get(totalLocations),
}));

const decodingStats = computed(() => ({
  completed: get(decodingCompleted),
  hasData: get(decodingTotal) > 0,
  isComplete: get(decodingCompleted) === get(decodingTotal) && get(decodingTotal) > 0,
  total: get(decodingTotal),
}));

const protocolCacheTotal = computed<number>(() => get(protocolCache).length);
const protocolCacheCompleted = computed<number>(() => get(protocolCache).filter(p => p.processed >= p.total).length);

const protocolCacheStats = computed(() => ({
  completed: get(protocolCacheCompleted),
  hasData: get(protocolCacheTotal) > 0,
  isComplete: get(protocolCacheCompleted) === get(protocolCacheTotal) && get(protocolCacheTotal) > 0,
  total: get(protocolCacheTotal),
}));
</script>

<template>
  <div class="flex items-center gap-3 px-3 py-2">
    <!-- Status Icon -->
    <RuiIcon
      :name="statusIcon"
      :class="[statusColor, { 'animate-spin': showSpinner }]"
      class="size-[18px] md:size-[20px] shrink-0"
    />

    <!-- Content Area -->
    <div class="flex-1 min-w-0 flex flex-col md:flex-row md:items-center gap-1 md:gap-3">
      <!-- Title Row -->
      <div class="flex items-center gap-3">
        <span class="font-medium text-sm text-rui-text whitespace-nowrap">
          {{ title }}
        </span>

        <!-- Progress Bar -->
        <div
          v-if="isSyncing"
          class="flex-1 max-w-[200px] md:max-w-xs"
        >
          <RuiProgress
            :value="overallProgress"
            color="primary"
            size="sm"
            rounded
          />
        </div>

        <!-- Progress Percentage -->
        <span
          v-if="isSyncing"
          class="text-xs text-rui-text-secondary tabular-nums"
        >
          {{ t('percentage_display.value', { value: overallProgress }) }}
        </span>
      </div>

      <!-- Stats -->
      <SyncProgressStats
        :chains="chainsStats"
        :locations="locationsStats"
        :decoding="decodingStats"
        :protocol-cache="protocolCacheStats"
        class="mt-0.5 md:mt-0"
      />
    </div>

    <!-- Action Buttons -->
    <div class="flex items-center gap-1 shrink-0">
      <RuiButton
        variant="text"
        icon
        size="sm"
        @click="emit('toggle')"
      >
        <RuiIcon
          :name="expanded ? 'lu-chevron-up' : 'lu-chevron-down'"
          size="16"
        />
      </RuiButton>

      <RuiButton
        v-if="canDismiss"
        variant="text"
        icon
        size="sm"
        @click="emit('dismiss')"
      >
        <RuiIcon
          name="lu-x"
          size="16"
        />
      </RuiButton>
    </div>
  </div>
</template>
