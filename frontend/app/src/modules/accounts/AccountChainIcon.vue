<script setup lang="ts">
import type { AccountChainState } from '@/modules/accounts/AccountChainsOverflow.vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const { item, filterable } = defineProps<{
  item: AccountChainState;
  /** Clicking hides the chain from the row's total, which takes a second chain to leave a total. */
  filterable: boolean;
}>();

const emit = defineEmits<{
  /** The click, which stays the row filter. */
  toggle: [enabled: boolean];
  /** The pointer entered the icon, for the row's menu to open on and anchor to. */
  point: [element: HTMLElement];
}>();

const { getChainName } = useSupportedChains();

function point(event: MouseEvent): void {
  if (event.currentTarget instanceof HTMLElement)
    emit('point', event.currentTarget);
}
</script>

<template>
  <div class="relative">
    <button
      type="button"
      class="rounded-full size-6 flex items-center justify-center dark:bg-white relative cursor-pointer transition-opacity focus-visible:focus-ring"
      :class="{ 'opacity-35': !item.enabled, 'ring-2 ring-rui-success-lighter dark:ring-rui-success': item.enabled && item.detected }"
      :aria-label="getChainName(item.chain)"
      :aria-pressed="filterable ? !item.enabled : undefined"
      :data-chain="item.chain"
      :data-detected="item.detected || undefined"
      data-testid="account-chain"
      @mouseenter="point($event)"
      @click="emit('toggle', !item.enabled)"
    >
      <ChainIcon
        :chain="item.chain"
        class="bg-transparent!"
        size="1.125"
      />
    </button>
    <div
      v-if="item.skipped"
      class="absolute -bottom-1 -right-1 flex items-center justify-center rounded-full bg-rui-error text-white p-0.5 border border-rui-surface z-3 pointer-events-none"
      data-testid="account-chain-skipped"
      :data-chain="item.chain"
    >
      <RuiIcon
        name="lu-ban"
        size="10"
      />
    </div>
  </div>
</template>
