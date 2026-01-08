<script setup lang="ts">
import type { ChainProgress } from '../types';
import ChainProgressItem from './ChainProgressItem.vue';

const props = defineProps<{
  chains: ChainProgress[];
}>();

const { t } = useI18n({ useScope: 'global' });

const showCompleted = ref<boolean>(false);

const inProgressChains = computed<ChainProgress[]>(() =>
  props.chains.filter(c => c.completed < c.total || c.total === 0),
);

const completedChains = computed<ChainProgress[]>(() =>
  props.chains.filter(c => c.completed === c.total && c.total > 0),
);

const hasInProgress = computed<boolean>(() => get(inProgressChains).length > 0);
const completedCount = computed<number>(() => get(completedChains).length);
const hasCompleted = computed<boolean>(() => !!get(completedCount));

function toggleCompleted(): void {
  set(showCompleted, !get(showCompleted));
}
</script>

<template>
  <div class="space-y-1 rounded-lg border border-default bg-rui-grey-50 dark:bg-rui-grey-800 p-2">
    <!-- In-progress chains shown first -->
    <ChainProgressItem
      v-for="chain in inProgressChains"
      :key="chain.chain"
      :chain="chain"
    />

    <!-- Completed chains collapsible section -->
    <div v-if="hasCompleted">
      <button
        v-if="!showCompleted"
        type="button"
        class="w-full flex items-center gap-2 py-2 px-2 text-sm text-rui-text-secondary hover:bg-rui-grey-100 dark:hover:bg-rui-grey-700 rounded-md transition-colors"
        :class="{ 'mt-2 border-t border-default pt-3': hasInProgress }"
        @click="toggleCompleted()"
      >
        <RuiIcon
          name="lu-circle-check"
          class="text-rui-success"
          size="16"
        />
        <span>{{ t('sync_progress.completed_chains', { count: completedCount }, completedCount) }}</span>
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
            name="lu-circle-check"
            class="text-rui-success"
            size="16"
          />
          <span>{{ t('sync_progress.completed_chains', { count: completedCount }, completedCount) }}</span>
          <RuiIcon
            name="lu-chevron-up"
            size="16"
            class="ml-auto"
          />
        </button>

        <div class="mt-1">
          <ChainProgressItem
            v-for="chain in completedChains"
            :key="chain.chain"
            :chain="chain"
            compact
          />
        </div>
      </template>
    </div>
  </div>
</template>
