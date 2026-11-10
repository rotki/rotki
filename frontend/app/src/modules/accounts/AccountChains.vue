<script lang="ts" setup>
import AccountChainIcon from '@/modules/accounts/AccountChainIcon.vue';
import AccountChainsHoverMenu from '@/modules/accounts/AccountChainsHoverMenu.vue';
import AccountChainsOverflow, { type AccountChainState } from '@/modules/accounts/AccountChainsOverflow.vue';
import { useDetectedAccountsStore } from '@/modules/accounts/use-detected-accounts-store';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';

type Row = ({ chain: string } | { chains: string[] }) & { id: string };

const chainFilter = defineModel<Record<string, string[]>>('chainFilter', { required: true });

const { address, row, skippable } = defineProps<{
  address?: string;
  row: Row;
  /** Whether the row is an address account, the only kind the backend matches a skip rule against. */
  skippable?: boolean;
}>();

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

const hoverMenuOpen = ref<boolean>(false);

const overflowMenuOpen = ref<boolean>(false);

function sameChains(set: Set<string>, chains: string[]): boolean {
  return set.size === chains.length && chains.every(chain => set.has(chain));
}

/**
 * The skipped chains the row keeps behind the "+N" rather than among its icons.
 *
 * @remarks
 * Held while one of the row's menus is open: skipping would otherwise pull the icon out from under
 * the menu that just skipped it. A single-chain row has no "+N" to park its only chain behind, so
 * it parks nothing. An unchanged set is handed back as it was, so the layout only recomputes on a
 * real change rather than on every filter click.
 */
const parkedChains = computed<Set<string>>((previous) => {
  if (previous && (get(hoverMenuOpen) || get(overflowMenuOpen)))
    return previous;

  const skipped = get(chains).length > 1 ? get(allChainStatus).filter(item => item.skipped).map(({ chain }) => chain) : [];
  return previous && sameChains(previous, skipped) ? previous : new Set(skipped);
});

/** Where each chain is drawn: as an icon, or behind the "+N" for lack of room or for being skipped. */
const layout = computed<{ icons: AccountChainState[]; overflow: AccountChainState[] }>(() => {
  const parked = get(parkedChains);
  const shown: AccountChainState[] = [];
  const hidden: AccountChainState[] = [];
  for (const item of get(allChainStatus))
    (parked.has(item.chain) ? hidden : shown).push(item);

  return {
    icons: shown.slice(0, MAX_VISIBLE_CHAINS),
    overflow: [...shown.slice(MAX_VISIBLE_CHAINS), ...hidden],
  };
});

/** The icons on the row, reversed because the row lays them out right to left for the overlap. */
const chainStatus = computed<AccountChainState[]>(() => [...get(layout).icons].reverse());

const overflowStatus = computed<AccountChainState[]>(() => get(layout).overflow);

const skipAddress = computed<string | undefined>(() => skippable ? address : undefined);

function updateChain(chain: string, enabled: boolean) {
  if (get(chains).length <= 1)
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
      v-model:open="overflowMenuOpen"
      :items="overflowStatus"
      :skip-address="skipAddress"
      @toggle="updateChain($event.chain, $event.enabled)"
    />
    <span
      v-if="chains.length === 1"
      class="text-body-2 text-rui-text"
      data-testid="account-chain-name"
    >
      {{ getChainName(chains[0]) }}
    </span>
    <AccountChainsHoverMenu
      v-model:open="hoverMenuOpen"
      :items="chainStatus"
      :filterable="chains.length > 1"
      :skip-address="skipAddress"
    >
      <template #default="{ point }">
        <AccountChainIcon
          v-for="item in chainStatus"
          :key="item.chain"
          :item="item"
          :filterable="chains.length > 1"
          @toggle="updateChain(item.chain, $event)"
          @point="point(item.chain, $event)"
        />
      </template>
    </AccountChainsHoverMenu>
  </div>
</template>
