<script lang="ts" setup>
import AccountChainsOverflow, { type AccountChainState } from '@/modules/accounts/AccountChainsOverflow.vue';
import { useDetectedAccountsStore } from '@/modules/accounts/use-detected-accounts-store';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

type Row = ({ chain: string } | { chains: string[] }) & { id: string };

const chainFilter = defineModel<Record<string, string[]>>('chainFilter', { required: true });

const { address, row } = defineProps<{ address?: string; row: Row }>();

const { t } = useI18n({ useScope: 'global' });

const chains = computed<string[]>(() => 'chains' in row ? row.chains : [row.chain]);

const { detectedChains, dismiss, isDetected } = useDetectedAccountsStore();
const { getChainName } = useSupportedChains();
const { isAddressExcluded } = useDisabledChains();

/**
 * Per chain: `enabled` is this row's local display filter, `skipped` is the saved setting, and
 * `detected` says account detection started tracking the address there since login.
 *
 * @remarks
 * Unrelated states on one icon, so they are drawn differently: the filter dims the icon, a skip
 * adds the ban badge that Settings uses for the same thing, and a detection colors the ring.
 * `isAddressExcluded` answers for a chain switched off whole as well, which is why a row can be
 * marked on a chain it has no rule of its own for.
 */
const allChainStatus = computed<AccountChainState[]>(() => {
  const activated = get(chains);
  const filter = get(chainFilter)[row.id] ?? [];
  return activated.map(chain => ({
    chain,
    detected: address !== undefined && isDetected(chain, address),
    enabled: !filter.includes(chain),
    skipped: address !== undefined && isAddressExcluded(chain, address),
  }));
});

/**
 * How many icons a row draws before the rest go behind a "+N" menu. Past this an account with many
 * chains widened the column enough to push the table sideways.
 */
const MAX_VISIBLE_CHAINS = 6;

/** The icons on the row, reversed because the row lays them out right to left for the overlap. */
const chainStatus = computed<AccountChainState[]>(() => get(allChainStatus).slice(0, MAX_VISIBLE_CHAINS).reverse());

const overflowStatus = computed<AccountChainState[]>(() => get(allChainStatus).slice(MAX_VISIBLE_CHAINS));

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

const anyDisabled = computed(() => get(allChainStatus).some(item => !item.enabled));

/**
 * The row's chains that detection added, named for the chip that explains the colored rings. The
 * chain tooltips stay about the click, so this is the one place the rings are explained.
 *
 * @remarks
 * Follows the row's chain order, which is the order the icons are drawn in.
 */
const detectedChainNames = computed<string[]>(() => {
  if (address === undefined)
    return [];

  const detectedHere = new Set(detectedChains(address));
  return get(chains)
    .filter(chain => detectedHere.has(chain))
    .map(chain => getChainName(chain));
});

function dismissDetection(): void {
  if (address !== undefined)
    dismiss(address);
}

function reset() {
  set(chainFilter, {
    ...get(chainFilter),
    [row.id]: [],
  });
}
</script>

<template>
  <div class="flex flex-row-reverse justify-end items-center gap-1.5 group">
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
    <RuiTooltip
      v-if="detectedChainNames.length > 0"
      :open-delay="200"
      :close-delay="0"
      :class-names="{ tooltip: 'max-w-80' }"
    >
      <template #activator>
        <RuiChip
          size="sm"
          color="success"
          clickable
          class="ml-2 self-center"
          data-testid="account-chains-detected"
          @click="dismissDetection()"
        >
          {{ t('account_balances.detected.chip') }}
        </RuiChip>
      </template>
      <span data-testid="account-chains-detected-tooltip">
        {{ t('account_balances.detected.tooltip', { chains: detectedChainNames.join(', ') }) }}
      </span>
    </RuiTooltip>
    <AccountChainsOverflow
      v-if="overflowStatus.length > 0"
      :items="overflowStatus"
      @toggle="updateChain($event.chain, $event.enabled)"
    />
    <!-- a lone chain is named, since there is nothing to filter and a bare icon is hard to place -->
    <span
      v-if="chains.length === 1"
      class="text-body-2 text-rui-text"
      data-testid="account-chain-name"
    >
      {{ getChainName(chains[0]) }}
    </span>
    <template
      v-for="item in chainStatus"
      :key="item.chain"
    >
      <RuiTooltip
        :close-delay="0"
        :class-names="{ tooltip: '-ml-1!' }"
      >
        <template #activator>
          <!--
            Bare icons side by side; dark mode keeps a small white backdrop, since several chain logos
            are drawn in black. A chain filtered out of the totals is dimmed, a detected one ringed.
          -->
          <div class="relative">
            <div
              class="rounded-full size-6 flex items-center justify-center dark:bg-white relative cursor-pointer transition-opacity"
              :class="{ 'opacity-35': !item.enabled, 'ring-2 ring-rui-success-lighter dark:ring-rui-success': item.enabled && item.detected }"
              :data-chain="item.chain"
              :data-detected="item.detected || undefined"
              data-testid="account-chain"
              @click="updateChain(item.chain, !item.enabled)"
            >
              <ChainIcon
                :chain="item.chain"
                class="bg-transparent!"
                size="1.125"
              />
            </div>
            <div
              v-if="item.skipped"
              class="absolute -bottom-1 -right-1 flex items-center justify-center rounded-full bg-rui-error text-white p-[2px] border border-rui-surface z-3"
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
