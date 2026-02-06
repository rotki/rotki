<script setup lang="ts">
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { AddressStatus, type ChainProgress } from '../types';
import AddressProgressItem from './AddressProgressItem.vue';

const props = withDefaults(defineProps<{
  chain: ChainProgress;
  compact?: boolean;
}>(), {
  compact: false,
});

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();

const chainName = getChainName(computed(() => props.chain.chain));

const INITIAL_SHOW_COUNT = 5;

const expanded = ref<boolean>(false);
const showAll = ref<boolean>(false);

const isComplete = computed<boolean>(() =>
  props.chain.completed === props.chain.total && props.chain.total > 0,
);

const hasActivity = computed<boolean>(() => props.chain.inProgress > 0);

const sortedAddresses = computed(() =>
  [...props.chain.addresses].sort((a, b) => {
    const priority: Record<string, number> = {
      [AddressStatus.QUERYING]: 0,
      [AddressStatus.DECODING]: 1,
      [AddressStatus.PENDING]: 2,
      [AddressStatus.COMPLETE]: 3,
    };
    return priority[a.status] - priority[b.status];
  }),
);

const visibleAddresses = computed(() => {
  if (get(showAll))
    return get(sortedAddresses);
  return get(sortedAddresses).slice(0, INITIAL_SHOW_COUNT);
});

const remainingCount = computed<number>(() =>
  Math.max(0, props.chain.addresses.length - INITIAL_SHOW_COUNT),
);

const hasMore = computed<boolean>(() => get(remainingCount) > 0 && !get(showAll));

const statusBorderColor = computed<string>(() => {
  if (get(isComplete))
    return 'border-l-rui-success';
  if (get(hasActivity))
    return 'border-l-rui-primary';
  return 'border-l-rui-grey-400 dark:border-l-rui-grey-600';
});

function toggleExpanded(): void {
  set(expanded, !get(expanded));
  if (!get(expanded)) {
    set(showAll, false);
  }
}

function showMore(): void {
  set(showAll, true);
}
</script>

<template>
  <div
    class="rounded-md border-l-2 transition-colors"
    :class="statusBorderColor"
  >
    <button
      type="button"
      class="w-full flex items-center gap-2 hover:bg-rui-grey-100 dark:hover:bg-rui-grey-700 rounded-r-md transition-colors"
      :class="compact ? 'py-1 px-2' : 'py-2 px-2 gap-3'"
      @click="toggleExpanded()"
    >
      <ChainIcon
        :chain="chain.chain"
        :size="compact ? '1rem' : '1.25rem'"
      />

      <span
        class="flex-1 font-medium text-left"
        :class="[
          compact ? 'text-xs' : 'text-sm',
          isComplete ? 'text-rui-text-secondary' : 'text-rui-text',
        ]"
      >
        {{ chainName }}
      </span>

      <div
        v-if="!isComplete"
        class="w-32"
      >
        <RuiProgress
          :value="chain.progress"
          :color="hasActivity ? 'primary' : 'secondary'"
          size="sm"
          rounded
        />
      </div>

      <span
        class="tabular-nums text-right min-w-[3rem]"
        :class="[
          compact ? 'text-xs' : 'text-sm',
          isComplete ? 'text-rui-text-disabled' : 'text-rui-text-secondary',
        ]"
      >
        {{ chain.completed }}/{{ chain.total }}
      </span>

      <RuiIcon
        v-if="isComplete"
        name="lu-check"
        class="text-rui-success"
        :size="compact ? 14 : 18"
      />
      <RuiIcon
        v-else-if="hasActivity"
        name="lu-loader-circle"
        class="text-rui-primary animate-spin"
        :size="compact ? 14 : 18"
      />
      <div
        v-else
        :class="compact ? 'w-[14px]' : 'w-[18px]'"
      />

      <RuiIcon
        :name="expanded ? 'lu-chevron-up' : 'lu-chevron-down'"
        class="text-rui-text-secondary"
        :size="compact ? 14 : 16"
      />
    </button>

    <div
      v-if="expanded"
      class="pr-2 pb-2 space-y-1"
      :class="compact ? 'pl-6' : 'pl-8'"
    >
      <AddressProgressItem
        v-for="address in visibleAddresses"
        :key="address.address"
        :address="address"
        :chain="chain.chain"
        :compact="compact"
      />

      <button
        v-if="hasMore"
        type="button"
        class="text-xs text-rui-primary hover:underline pl-2"
        @click.stop="showMore()"
      >
        {{ t('sync_progress.show_more', { count: remainingCount }) }}
      </button>
    </div>
  </div>
</template>
