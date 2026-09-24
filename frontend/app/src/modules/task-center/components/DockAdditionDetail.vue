<script setup lang="ts">
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const { added, everyChain, existed, failed, noActivity } = defineProps<{
  added: readonly string[];
  everyChain: boolean;
  existed: readonly string[];
  noActivity: readonly string[];
  failed: readonly string[];
}>();

const { t } = useI18n({ useScope: 'global' });

const { getChainName } = useSupportedChains();

/** How many chain icons the row shows before it only counts the rest. */
const SHOWN_ICONS = 6;

/**
 * How many failed chains the row names before it only counts them. A user without a paid indexer
 * key fails the same half-dozen chains on every addition, and naming them all wraps the row.
 */
const NAMED_FAILURES = 3;

const shownChains = computed<readonly string[]>(() => added.slice(0, SHOWN_ICONS));

const hiddenCount = computed<number>(() => Math.max(0, added.length - SHOWN_ICONS));

const addedNames = computed<string>(() => added.map(chain => getChainName(chain)).join(', '));

/**
 * The chains it was not added on and nothing went wrong, counted rather than named: a dozen chain
 * names where the address has no activity yet is noise, not a dozen facts.
 */
const skippedLine = computed<string>(() => [
  noActivity.length > 0 ? t('task_dock.detail.addition.no_activity', { count: noActivity.length }, noActivity.length) : '',
  existed.length > 0 ? t('task_dock.detail.addition.existed', { count: existed.length }, existed.length) : '',
].filter(Boolean).join(' · '));

const failedNames = computed<string>(() => failed.map(chain => getChainName(chain)).join(', '));

const failedLine = computed<string>(() => {
  if (failed.length === 0)
    return '';
  if (failed.length > NAMED_FAILURES)
    return t('task_dock.detail.addition.failed_count', { count: failed.length }, failed.length);
  return t('task_dock.detail.addition.failed', { chains: get(failedNames) });
});
</script>

<template>
  <div
    class="flex flex-col gap-0.5 text-xs leading-4 text-rui-text-secondary"
    data-testid="dock-addition-detail"
  >
    <span v-if="everyChain">{{ t('task_dock.detail.addition.every_chain') }}</span>
    <div
      v-else-if="added.length > 0"
      class="flex items-center gap-1.5 min-w-0"
      :title="addedNames"
      data-testid="dock-addition-added"
    >
      <span class="shrink-0">{{ t('task_dock.detail.addition.tracked_on') }}</span>
      <div class="flex items-center gap-0.5 min-w-0">
        <ChainIcon
          v-for="chain in shownChains"
          :key="chain"
          class="shrink-0"
          :chain="chain"
          size="0.875rem"
        />
        <span
          v-if="hiddenCount > 0"
          class="shrink-0 ml-0.5 tabular-nums"
        >
          {{ t('task_dock.detail.addition.more', { count: hiddenCount }) }}
        </span>
      </div>
    </div>
    <span
      v-if="skippedLine"
      data-testid="dock-addition-skipped"
    >
      {{ skippedLine }}
    </span>
    <span
      v-if="failedLine"
      class="text-rui-error break-words"
      :title="failedNames"
      data-testid="dock-addition-failed"
    >
      {{ failedLine }}
    </span>
  </div>
</template>
