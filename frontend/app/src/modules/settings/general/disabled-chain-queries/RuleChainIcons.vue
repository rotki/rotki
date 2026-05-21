<script setup lang="ts">
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

defineProps<{
  chainIds: readonly string[];
  chainNameFor: (chainId: string) => string;
  emptyLabel: string;
}>();
</script>

<template>
  <div class="flex items-center gap-1 shrink-0">
    <RuiTooltip
      v-for="chainId in chainIds"
      :key="chainId"
      :popper="{ placement: 'top' }"
      :open-delay="300"
    >
      <template #activator>
        <ChainIcon
          :chain="chainId"
          size="18px"
        />
      </template>
      {{ chainNameFor(chainId) }}
    </RuiTooltip>
    <span
      v-if="chainIds.length === 0"
      class="text-rui-text-secondary text-sm"
    >
      {{ emptyLabel }}
    </span>
  </div>
</template>
