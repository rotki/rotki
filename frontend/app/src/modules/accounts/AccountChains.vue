<script lang="ts" setup>
import { uniqueStrings } from '@/modules/core/common/data/data';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

type Row = ({ chain: string } | { chains: string[] }) & { id: string };

const chainFilter = defineModel<Record<string, string[]>>('chainFilter', { required: true });

const { address, row } = defineProps<{ address?: string; row: Row }>();

const { t } = useI18n({ useScope: 'global' });

const chains = computed<string[]>(() => 'chains' in row ? row.chains : [row.chain]);

const { getChainName } = useSupportedChains();
const { isAddressExcluded } = useDisabledChains();

/**
 * Per chain: `enabled` is this row's local display filter, `skipped` is the saved setting.
 *
 * @remarks
 * Two unrelated states on one icon, so they are drawn differently: the filter dims the icon, while
 * a skip adds the ban badge that Settings uses for the same thing. `isAddressExcluded` answers for
 * a chain switched off whole as well, which is why a row can be marked on a chain it has no rule of
 * its own for.
 */
const chainStatus = computed<{ chain: string; enabled: boolean; skipped: boolean }[]>(() => {
  const activated = get(chains);
  const filter = get(chainFilter)[row.id] ?? [];
  return activated.map(chain => ({
    chain,
    enabled: !filter.includes(chain),
    skipped: address !== undefined && isAddressExcluded(chain, address),
  })).reverse();
});

function updateChain(chain: string, enabled: boolean) {
  if (!(get(chains).length > 1))
    return;

  const currentFilter = get(chainFilter)[row.id] ?? [];
  if (!enabled) {
    set(chainFilter, {
      ...get(chainFilter),
      [row.id]: [...currentFilter, chain].filter(uniqueStrings),
    });
  }
  else {
    const updatedFilter = { ...get(chainFilter) };
    const excluded = currentFilter.filter(entry => entry !== chain);
    if (excluded.length === 0)
      delete updatedFilter[row.id];
    else
      updatedFilter[row.id] = excluded;

    set(chainFilter, updatedFilter);
  }
}

const anyDisabled = computed(() => get(chainStatus).some(item => !item.enabled));

function reset() {
  set(chainFilter, {
    ...get(chainFilter),
    [row.id]: [],
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
          data-testid="account-chain-filter-clear"
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
        :class-names="{ tooltip: '!-ml-1' }"
      >
        <template #activator>
          <div class="relative -ml-2 z-[0] hover:z-[1]">
            <div
              class="rounded-full w-8 h-8 bg-rui-grey-300 dark:bg-white flex items-center justify-center border-2 border-white dark:border-rui-grey-300 relative cursor-pointer transition-all overflow-hidden"
              :class="{ '!border-0': !item.enabled }"
              :data-chain="item.chain"
              data-testid="account-chain"
              @click="updateChain(item.chain, !item.enabled)"
            >
              <ChainIcon
                :chain="item.chain"
                class="!bg-transparent"
                size="1"
              />
              <div
                class="absolute top-0 left-0 w-full h-full opacity-0 bg-black z-[2] transition-all"
                :class="{ 'opacity-40 dark:opacity-60': !item.enabled } "
              />
            </div>
            <div
              v-if="item.skipped"
              class="absolute -bottom-0.5 -right-0.5 flex items-center justify-center rounded-full bg-rui-error text-white p-[2px] border border-rui-bg z-[3]"
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

        <div
          v-if="item.skipped"
          data-testid="account-chain-skipped-tooltip"
        >
          {{ t('account_balances.skip_queries.chain_marker', { chain: getChainName(item.chain) }) }}
        </div>

        <template v-if="chains.length > 1">
          <i18n-t
            v-if="item.enabled"
            scope="global"
            keypath="account_balances.chain_filter.remove"
            tag="span"
          >
            <template #chain>
              <b>{{ getChainName(item.chain) }}</b>
            </template>
          </i18n-t>
          <i18n-t
            v-else
            scope="global"
            keypath="account_balances.chain_filter.add"
            tag="span"
          >
            <template #chain>
              <b>{{ getChainName(item.chain) }}</b>
            </template>
          </i18n-t>
        </template>
        <template v-else-if="!item.skipped">
          {{ getChainName(item.chain) }}
        </template>
      </RuiTooltip>
    </template>
  </div>
</template>
