<script setup lang="ts">
import type { ProtocolCacheProgress } from '../types';
import ProtocolCacheProgressItem from './ProtocolCacheProgressItem.vue';

const { protocolCache } = defineProps<{
  protocolCache: ProtocolCacheProgress[];
}>();

const { t } = useI18n({ useScope: 'global' });

const showCompleted = ref<boolean>(false);

const inProgressCache = computed<ProtocolCacheProgress[]>(() =>
  protocolCache.filter(p => p.processed < p.total && !p.cancelled),
);

const completedCache = computed<ProtocolCacheProgress[]>(() =>
  protocolCache.filter(p => p.processed >= p.total || p.cancelled),
);

const hasCancelledItems = computed<boolean>(() =>
  get(completedCache).some(p => p.cancelled),
);

const completedIconColor = computed<string>(() =>
  get(hasCancelledItems) ? 'text-rui-warning' : 'text-rui-success',
);

const hasInProgress = computed<boolean>(() => get(inProgressCache).length > 0);
const completedCount = computed<number>(() => get(completedCache).length);
const hasCompleted = computed<boolean>(() => !!get(completedCount));

// A cancelled protocol never got refreshed, so the summary says the group finished rather than
// claiming every one of them was refreshed.
const completedLabel = computed<string>(() => {
  const count = get(completedCount);
  return get(hasCancelledItems)
    ? t('sync_progress.finished_protocol_cache', { count }, count)
    : t('sync_progress.completed_protocol_cache', { count }, count);
});

const completedIcon = computed<string>(() => (get(hasCancelledItems) ? 'lu-circle-alert' : 'lu-circle-check'));

function toggleCompleted(): void {
  set(showCompleted, !get(showCompleted));
}
</script>

<template>
  <div class="space-y-1 rounded-lg border border-default bg-rui-grey-50 dark:bg-rui-grey-800 p-2">
    <!-- In-progress protocol cache shown first -->
    <ProtocolCacheProgressItem
      v-for="item in inProgressCache"
      :key="`${item.chain}-${item.protocol}`"
      :item="item"
    />

    <!-- Completed protocol cache collapsible section -->
    <div v-if="hasCompleted">
      <button
        v-if="!showCompleted"
        type="button"
        class="w-full flex items-center gap-2 py-2 px-2 text-sm text-rui-text-secondary hover:bg-rui-grey-100 dark:hover:bg-rui-grey-700 rounded-md transition-colors"
        :class="{ 'mt-2 border-t border-default pt-3': hasInProgress }"
        @click="toggleCompleted()"
      >
        <RuiIcon
          :name="completedIcon"
          :class="completedIconColor"
          size="16"
        />
        <span>{{ completedLabel }}</span>
        <RuiIcon
          name="lu-chevron-down"
          size="16"
          class="ml-auto"
        />
      </button>

      <template v-else>
        <button
          type="button"
          class="w-full flex items-center gap-2 py-2 px-2 text-sm text-rui-text-secondary hover:bg-rui-grey-100 dark:hover:bg-rui-grey-700 rounded-md transition-colors"
          :class="{ 'mt-2 border-t border-default pt-3': hasInProgress }"
          @click="toggleCompleted()"
        >
          <RuiIcon
            :name="completedIcon"
            :class="completedIconColor"
            size="16"
          />
          <span>{{ completedLabel }}</span>
          <RuiIcon
            name="lu-chevron-up"
            size="16"
            class="ml-auto"
          />
        </button>

        <div class="mt-1">
          <ProtocolCacheProgressItem
            v-for="item in completedCache"
            :key="`${item.chain}-${item.protocol}`"
            :item="item"
            compact
          />
        </div>
      </template>
    </div>
  </div>
</template>
