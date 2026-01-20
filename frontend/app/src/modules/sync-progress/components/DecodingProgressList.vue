<script setup lang="ts">
import type { DecodingProgress } from '../types';
import DecodingProgressItem from './DecodingProgressItem.vue';

const props = defineProps<{
  decoding: DecodingProgress[];
}>();

const { t } = useI18n({ useScope: 'global' });

const showCompleted = ref<boolean>(false);

const inProgressDecoding = computed<DecodingProgress[]>(() =>
  props.decoding.filter(d => d.processed < d.total),
);

const completedDecoding = computed<DecodingProgress[]>(() =>
  props.decoding.filter(d => d.processed >= d.total),
);

const hasInProgress = computed<boolean>(() => get(inProgressDecoding).length > 0);
const completedCount = computed<number>(() => get(completedDecoding).length);
const hasCompleted = computed<boolean>(() => !!get(completedCount));

function toggleCompleted(): void {
  set(showCompleted, !get(showCompleted));
}
</script>

<template>
  <div class="space-y-1 rounded-lg border border-default bg-rui-grey-50 dark:bg-rui-grey-800 p-2">
    <!-- In-progress decoding shown first -->
    <DecodingProgressItem
      v-for="item in inProgressDecoding"
      :key="item.chain"
      :item="item"
    />

    <!-- Completed decoding collapsible section -->
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
        <span>{{ t('sync_progress.completed_decoding', { count: completedCount }, completedCount) }}</span>
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
          <span>{{ t('sync_progress.completed_decoding', { count: completedCount }, completedCount) }}</span>
          <RuiIcon
            name="lu-chevron-up"
            size="16"
            class="ml-auto"
          />
        </button>

        <div class="mt-1">
          <DecodingProgressItem
            v-for="item in completedDecoding"
            :key="item.chain"
            :item="item"
            compact
          />
        </div>
      </template>
    </div>
  </div>
</template>
