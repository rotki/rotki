<script lang="ts" setup>
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { uniqueStrings } from '@/utils/data';

type Row = ({ chain: string } | { chains: string[] }) & { id: string };

const chainFilter = defineModel<Record<string, string[]>>('chainFilter', { required: true });

const props = defineProps<{ row: Row }>();

const { t } = useI18n();

const chains = computed<string[]>(() => {
  const row = props.row;
  return 'chains' in row ? row.chains : [row.chain];
});

const { getChainName } = useSupportedChains();

const chainStatus = computed<{ chain: string; enabled: boolean }[]>(() => {
  const activated = get(chains);
  const filter = get(chainFilter)[props.row.id] ?? [];
  return activated.map(chain => ({ chain, enabled: !filter.includes(chain) })).reverse();
});

function updateChain(chain: string, enabled: boolean) {
  if (!(get(chains).length > 1))
    return;

  const currentFilter = get(chainFilter)[props.row.id] ?? [];
  if (!enabled) {
    set(chainFilter, {
      ...get(chainFilter),
      [props.row.id]: [...currentFilter, chain].filter(uniqueStrings),
    });
  }
  else {
    const updatedFilter = { ...get(chainFilter) };
    const excluded = currentFilter.filter(entry => entry !== chain);
    if (excluded.length === 0)
      delete updatedFilter[props.row.id];
    else
      updatedFilter[props.row.id] = excluded;

    set(chainFilter, updatedFilter);
  }
}

const anyDisabled = computed(() => get(chainStatus).some(item => !item.enabled));

function reset() {
  set(chainFilter, {
    ...get(chainFilter),
    [props.row.id]: [],
  });
}
</script>

<template>
  <div class="flex flex-row-reverse justify-end pl-2 group">
    <RuiTooltip
      :disabled="!anyDisabled"
      :open-delay="400"
      :close-delay="0"
    >
      <template #activator>
        <RuiButton
          size="sm"
          icon
          class="opacity-0 transition invisible"
          :class="{
            'group-hover:opacity-100 group-hover:visible': anyDisabled,
          }"
          variant="text"
          @click="reset()"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </template>
      {{ t('account_balances.chain_filter.clear') }}
    </RuiTooltip>
    <template
      v-for="item in chainStatus"
      :key="item.chain"
    >
      <RuiTooltip
        :close-delay="0"
        tooltip-class="!-ml-1"
      >
        <template #activator>
          <div
            class="rounded-full w-8 h-8 bg-rui-grey-300 dark:bg-white flex items-center justify-center border-2 border-white dark:border-rui-grey-300 -ml-2 relative z-[0] hover:z-[1] cursor-pointer account-chain transition-all overflow-hidden"
            :class="{ '!border-0': !item.enabled }"
            :data-chain="item.chain"
            @click="updateChain(item.chain, !item.enabled)"
          >
            <ChainIcon
              :chain="item.chain"
              size="1"
            />
            <div
              class="absolute top-0 left-0 w-full h-full opacity-0 bg-black z-[2] transition-all"
              :class="{ 'opacity-40 dark:opacity-60': !item.enabled } "
            />
          </div>
        </template>

        <template v-if="chains.length > 1">
          <i18n-t
            v-if="item.enabled"
            keypath="account_balances.chain_filter.remove"
            tag="span"
          >
            <template #chain>
              <b>{{ getChainName(item.chain) }}</b>
            </template>
          </i18n-t>
          <i18n-t
            v-else
            keypath="account_balances.chain_filter.add"
            tag="span"
          >
            <template #chain>
              <b>{{ getChainName(item.chain) }}</b>
            </template>
          </i18n-t>
        </template>
        <template v-else>
          {{ getChainName(item.chain) }}
        </template>
      </RuiTooltip>
    </template>
  </div>
</template>
