<script setup lang="ts">
import type { BackendProblem, ProblemItem } from '@/modules/core/notifications/problems/backend-problem-tree';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { type ProblemItemAction, useBackendProblemActions } from '@/modules/core/notifications/problems/use-backend-problem-actions';
import { type ProblemItemHeading, useBackendProblemText } from '@/modules/core/notifications/problems/use-backend-problem-text';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

const { item, problem, showTime = false } = defineProps<{
  problem: BackendProblem;
  item: ProblemItem;
  /** Whether the row names when it was last seen; a problem with one item shows that on its card. */
  showTime?: boolean;
}>();

const emit = defineEmits<{
  acted: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { copy } = useClipboard();
const { itemDetails, itemHeading } = useBackendProblemText();
const { itemAction } = useBackendProblemActions();

const heading = computed<ProblemItemHeading>(() => itemHeading(item));
const action = computed<ProblemItemAction | undefined>(() => itemAction(problem, item));

/** When the asset's price is missing, for a missing-price row; null for every other row. */
const pricedAt = computed<number | null>(() => {
  const current = get(heading);
  return current.kind === 'asset' ? current.timestamp : null;
});

const hasSubline = computed<boolean>(() => showTime || get(pricedAt) !== null);

function run(): void {
  const current = get(action);
  if (!current)
    return;

  current.run();
  emit('acted');
}

async function copyDetails(): Promise<void> {
  await copy(itemDetails(item));
}
</script>

<template>
  <div
    class="flex items-center gap-1.5 min-w-0 py-2 ps-3.5 pe-1.5 border-t border-default"
    data-testid="backend-problem-item"
  >
    <div class="flex-1 min-w-0 flex flex-col gap-0.5">
      <div class="flex items-center gap-1.5 min-w-0 text-body-2">
        <div class="min-w-0 font-medium truncate">
          <AssetDetails
            v-if="heading.kind === 'asset'"
            :asset="heading.asset"
            :display="{ dense: true, inline: true, size: '20px' }"
            :actions="{ hideMenu: true }"
          />
          <DateDisplay
            v-else-if="heading.kind === 'date'"
            :timestamp="heading.date.getTime()"
            milliseconds
          />
          <span
            v-else
            :title="heading.full ?? heading.text"
          >
            {{ heading.text }}
          </span>
        </div>
        <span
          v-if="item.repeats > 1"
          class="shrink-0 text-caption text-rui-text-secondary"
          data-testid="backend-problem-item-repeats"
        >
          {{ t('backend_problems.repeats', { count: item.repeats }) }}
        </span>
      </div>
      <div
        v-if="hasSubline"
        class="flex flex-wrap items-center gap-x-2 text-caption text-rui-text-secondary"
      >
        <i18n-t
          v-if="pricedAt !== null"
          scope="global"
          keypath="backend_problems.priced_at"
          tag="span"
        >
          <template #date>
            <DateDisplay :timestamp="pricedAt" />
          </template>
        </i18n-t>
        <TimeAgoDisplay
          v-if="showTime"
          :timestamp="item.lastSeen.getTime()"
          milliseconds
        />
      </div>
    </div>
    <RuiButton
      v-if="action"
      class="shrink-0"
      color="primary"
      variant="text"
      size="sm"
      data-testid="backend-problem-item-action"
      @click="run()"
    >
      {{ action.label }}
    </RuiButton>
    <RuiTooltip
      :open-delay="400"
      class="shrink-0"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="text-rui-text-secondary!"
          :aria-label="t('backend_problems.actions.copy_details')"
          data-testid="backend-problem-item-copy"
          @click="copyDetails()"
        >
          <RuiIcon
            name="lu-copy"
            size="16"
          />
        </RuiButton>
      </template>
      {{ t('backend_problems.actions.copy_details') }}
    </RuiTooltip>
  </div>
</template>
