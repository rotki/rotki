<script setup lang="ts">
import DockCacheRow from '@/modules/task-center/components/DockCacheRow.vue';

interface DockCache {
  readonly chain: string;
  readonly protocol: string;
  readonly processed: number;
  readonly total: number;
}

const { filled, filling, stopped } = defineProps<{
  filling: DockCache[];
  filled: DockCache[];
  /** Left unfinished by work that has settled; listed openly, since they are what did not get done. */
  stopped: DockCache[];
}>();

const { t } = useI18n({ useScope: 'global' });

/** Full caches are the record of what the work touched, so they wait behind a click while the filling ones show. */
const showFilled = ref<boolean>(false);

function cacheKey(cache: DockCache): string {
  return `${cache.chain}#${cache.protocol}`;
}
</script>

<template>
  <div
    class="flex flex-col"
    data-testid="dock-cache-list"
  >
    <DockCacheRow
      v-for="cache in filling"
      :key="cacheKey(cache)"
      v-bind="cache"
    />
    <DockCacheRow
      v-for="cache in stopped"
      :key="cacheKey(cache)"
      v-bind="cache"
      stopped
    />
    <button
      v-if="filled.length > 0"
      type="button"
      class="flex items-center gap-1.5 text-xs leading-5 text-rui-text-secondary hover:text-rui-text"
      :aria-expanded="showFilled"
      data-testid="dock-cache-filled-toggle"
      @click="showFilled = !showFilled"
    >
      <RuiIcon
        name="lu-circle-check"
        size="14"
        class="text-rui-success"
      />
      {{ t('task_dock.detail.caches_filled', { count: filled.length }, filled.length) }}
      <RuiIcon
        :name="showFilled ? 'lu-chevron-up' : 'lu-chevron-down'"
        size="14"
      />
    </button>
    <template v-if="showFilled">
      <DockCacheRow
        v-for="cache in filled"
        :key="cacheKey(cache)"
        v-bind="cache"
      />
    </template>
  </div>
</template>
