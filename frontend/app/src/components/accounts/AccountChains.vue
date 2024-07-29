<script lang="ts" setup>
type Row = { chain: string } | { chains: string[] };

const props = defineProps<{ row: Row }>();

const emit = defineEmits<{
  (e: 'update:chain', chain: string): void;
}>();

const chains = computed<string[]>(() => {
  const row = props.row;
  return 'chains' in row ? [...row.chains].reverse() : [row.chain];
});

const { getChainName } = useSupportedChains();
</script>

<template>
  <div class="flex flex-row-reverse justify-end pl-2">
    <template
      v-for="chain in chains"
      :key="chain"
    >
      <RuiTooltip
        :close-delay="0"
        tooltip-class="!-ml-1"
      >
        <template #activator>
          <div
            class="rounded-full w-8 h-8 bg-rui-grey-300 dark:bg-white flex items-center justify-center border-2 border-white dark:border-rui-grey-300 -ml-2 relative z-[0] hover:z-[1] cursor-pointer account-chain"
            :data-chain="chain"
            @click="emit('update:chain', chain)"
          >
            <ChainIcon
              :chain="chain"
              size="1"
            />
          </div>
        </template>
        {{ getChainName(chain) }}
      </RuiTooltip>
    </template>
  </div>
</template>
