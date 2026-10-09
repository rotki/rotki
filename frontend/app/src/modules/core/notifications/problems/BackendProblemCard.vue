<script setup lang="ts">
import type { BackendProblem, ProblemItem } from '@/modules/core/notifications/problems/backend-problem-tree';
import BackendProblemItem from '@/modules/core/notifications/problems/BackendProblemItem.vue';
import { useBackendProblemText } from '@/modules/core/notifications/problems/use-backend-problem-text';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

const { problem } = defineProps<{
  problem: BackendProblem;
}>();

const emit = defineEmits<{
  dismiss: [id: string];
  acted: [];
}>();

const { t } = useI18n({ useScope: 'global' });

/** Items an expanded card shows before it asks to show the rest. */
const PREVIEW_ITEMS = 5;

const expanded = ref<boolean>(false);
const showAll = ref<boolean>(false);

const { problemTitle } = useBackendProblemText();

const isError = computed<boolean>(() => problem.verbosity === 'error');

const visibleItems = computed<readonly ProblemItem[]>(() => (get(showAll) ? problem.items : problem.items.slice(0, PREVIEW_ITEMS)));

/** Items held back until the user asks for them. */
const previewRest = computed<number>(() => problem.items.length - get(visibleItems).length);

/** Items past the store's cap, which no toggle can show. */
const hiddenItems = computed<number>(() => problem.itemTotal - problem.items.length);

/** One item's time is the card's own, so only a card with several items times each one. */
const timesItems = computed<boolean>(() => problem.items.length > 1);

function toggle(): void {
  set(expanded, !get(expanded));
}
</script>

<template>
  <RuiCard
    class="p-0! h-auto! max-w-100 overflow-hidden"
    :class="isError ? 'border-rui-error-border' : 'border-rui-warning-border'"
    no-padding
    variant="outlined"
    data-testid="backend-problem"
  >
    <div class="flex items-center px-2 py-2.5 overflow-hidden">
      <button
        type="button"
        class="flex flex-1 items-center min-w-0 text-start cursor-pointer"
        tabindex="-1"
        data-testid="backend-problem-header"
        @click="toggle()"
      >
        <span
          class="mr-3 ml-1 rounded-full p-1.5"
          :class="isError ? 'bg-rui-error-soft text-rui-error' : 'bg-rui-warning-soft text-rui-warning'"
        >
          <RuiIcon
            size="18"
            :name="isError ? 'lu-circle-alert' : 'lu-siren'"
          />
        </span>
        <span class="flex-1 min-w-0">
          <span
            class="block font-medium line-clamp-2 break-words"
            :title="problemTitle(problem)"
          >
            {{ problemTitle(problem) }}
          </span>
          <span class="mt-0.5 flex flex-wrap gap-x-2 text-caption text-rui-text-secondary">
            <span
              class="whitespace-nowrap"
              data-testid="backend-problem-count"
            >
              {{ t('backend_problems.summary', {
                problems: t('backend_problems.count', { count: problem.itemTotal }, problem.itemTotal),
                seen: t('backend_problems.seen', { count: problem.repeats }, problem.repeats),
              }) }}
            </span>
            <TimeAgoDisplay
              class="whitespace-nowrap"
              :timestamp="problem.lastSeen.getTime()"
              milliseconds
            />
          </span>
        </span>
      </button>
      <RuiButton
        variant="text"
        icon
        size="sm"
        class="shrink-0 text-rui-text-secondary!"
        data-testid="backend-problem-toggle"
        :aria-expanded="expanded"
        @click="toggle()"
      >
        <RuiIcon
          size="18"
          :name="expanded ? 'lu-chevron-up' : 'lu-chevron-down'"
        />
      </RuiButton>
      <RuiButton
        variant="text"
        icon
        size="sm"
        class="shrink-0 text-rui-text-secondary!"
        data-testid="backend-problem-dismiss"
        @click="emit('dismiss', problem.id)"
      >
        <RuiIcon
          size="18"
          name="lu-x"
        />
      </RuiButton>
    </div>
    <div v-if="expanded">
      <BackendProblemItem
        v-for="item in visibleItems"
        :key="item.identity"
        :problem="problem"
        :item="item"
        :show-time="timesItems"
        @acted="emit('acted')"
      />
      <div
        v-if="previewRest > 0 || showAll"
        class="px-1.5 py-0.5 border-t border-default"
      >
        <RuiButton
          variant="text"
          color="primary"
          size="sm"
          data-testid="backend-problem-show-all"
          @click="showAll = !showAll"
        >
          {{ showAll ? t('backend_problems.show_fewer') : t('backend_problems.show_rest', { count: previewRest }) }}
        </RuiButton>
      </div>
      <div
        v-if="hiddenItems > 0 && previewRest === 0"
        class="px-3 py-1.5 border-t border-default text-caption text-rui-text-secondary"
        data-testid="backend-problem-more"
      >
        {{ t('backend_problems.more', { count: hiddenItems }) }}
      </div>
    </div>
  </RuiCard>
</template>
