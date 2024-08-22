<script lang="ts" setup>
type Row = ({ chain: string } | { chains: string[] }) & {
  fullChains?: string[];
};

const props = defineProps<{
  row: Row;
  availableChains: string[];
}>();

const chainFilter = defineModel<string[]>('chainFilter', { required: true });

const chains = computed<string[]>(() => {
  const row = props.row;
  return 'chains' in row ? row.chains : [row.chain];
});

const { getChainName } = useSupportedChains();
const aggregatedChains = computed<{ chain: string; enabled: boolean }[]>(() => {
  const full = props.row.fullChains;
  const activated = get(chains);

  if (!full)
    return activated.map(chain => ({ chain, enabled: true })).reverse();

  return full.map(chain => ({ chain, enabled: activated.includes(chain) })).reverse();
});

function updateChain(chain: string, enabled: boolean) {
  if (get(chains).length <= 1)
    return;

  const currentFilter = get(chainFilter);
  const available = props.availableChains;

  if (currentFilter.length === 0 && !enabled) {
    set(chainFilter, available.filter(item => item !== chain));
    return;
  }

  let newValue = [
    ...currentFilter,
  ];

  const index = newValue.indexOf(chain);

  if (enabled && index === -1)
    newValue.push(chain);
  else if (!enabled && index > -1)
    newValue.splice(index, 1);

  if (newValue.length === available.length)
    newValue = [];

  set(chainFilter, newValue);
}
</script>

<template>
  <div class="flex flex-row-reverse justify-end pl-2">
    <template
      v-for="chain in aggregatedChains"
      :key="chain.chain"
    >
      <RuiTooltip
        :close-delay="0"
        tooltip-class="!-ml-1"
      >
        <template #activator>
          <div
            class="rounded-full w-8 h-8 bg-rui-grey-300 dark:bg-white flex items-center justify-center border-2 border-white dark:border-rui-grey-300 -ml-2 relative z-[0] hover:z-[1] cursor-pointer account-chain transition-all overflow-hidden"
            :class="{ '!border-0': !chain.enabled }"
            :data-chain="chain.chain"
            @click="updateChain(chain.chain, !chain.enabled)"
          >
            <ChainIcon
              :chain="chain.chain"
              size="1"
            />
            <div
              class="absolute top-0 left-0 w-full h-full opacity-0 bg-black z-[2] transition-all"
              :class="{ 'opacity-40 dark:opacity-60': !chain.enabled } "
            />
          </div>
        </template>

        <template v-if="chains.length > 1">
          <i18n-t
            v-if="chain.enabled"
            keypath="account_balances.chain_filter.remove"
            tag="span"
          >
            <template #chain>
              <b>{{ getChainName(chain.chain) }}</b>
            </template>
          </i18n-t>
          <i18n-t
            v-else
            keypath="account_balances.chain_filter.add"
            tag="span"
          >
            <template #chain>
              <b>{{ getChainName(chain.chain) }}</b>
            </template>
          </i18n-t>
        </template>
        <template v-else>
          {{ getChainName(chain.chain) }}
        </template>
      </RuiTooltip>
    </template>
  </div>
</template>
