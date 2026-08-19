<script setup lang="ts">
import type { TradableAsset } from '@/modules/wallet/types';
import { type BigNumber, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import TradeAssetDisplay from '@/modules/wallet/send/TradeAssetDisplay.vue';
import { useBalanceQueries } from '@/modules/wallet/send/use-balance-queries';
import { useTradeAssetNavigation } from '@/modules/wallet/send/use-trade-asset-navigation';
import { ALL_CHAINS, type TradeAssetOption, useTradeAssetOptions } from '@/modules/wallet/send/use-trade-asset-options';
import { useInjectedTradableAsset } from '@/modules/wallet/use-tradable-asset';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';

const asset = defineModel<string>({ required: true });
const chain = defineModel<string>('chain', { required: true });

const { address, amount } = defineProps<{
  address?: string;
  amount: BigNumber | undefined;
}>();

const emit = defineEmits<{
  'set-max': [];
  'refresh': [];
}>();

/** Row height in px, matching the padded two-line row below. The virtual list needs it up front. */
const ITEM_HEIGHT = 56;

const openDialog = ref<boolean>(false);
const internalChain = ref<string>(Blockchain.ETH);
const search = ref<string>('');
const searchField = useTemplateRef<HTMLInputElement>('searchField');

const { t } = useI18n({ useScope: 'global' });

const { allOwnedAssets, getAssetDetail } = useInjectedTradableAsset();

const { connected, connectedAddress, supportedChainsForConnectedAccount } = storeToRefs(useWalletStore());
const { useIsActive } = useTaskCenter();

const isDetecting = useIsActive(ActivityKind.TOKEN_DETECTION);

const { useQueryingBalances } = useBalanceQueries(connected, connectedAddress);

const assetDetail = getAssetDetail(asset, chain);

const chainOptions = computed<string[]>(() => [
  ALL_CHAINS,
  ...get(supportedChainsForConnectedAccount),
]);

// Latched rather than tracking `openDialog`: once the names are resolved they are cached, and
// dropping back to identifier ordering on close would reshuffle the list between openings.
const namesNeeded = ref<boolean>(false);

const { options: assetOptions, orderedAssets } = useTradeAssetOptions(
  allOwnedAssets,
  internalChain,
  search,
  supportedChainsForConnectedAccount,
  namesNeeded,
);

const { containerProps, list, scrollTo, wrapperProps } = useVirtualList(assetOptions, {
  itemHeight: ITEM_HEIGHT,
  overscan: 6,
});

function selectAsset(item: TradableAsset): void {
  set(chain, item.chain);
  set(asset, item.asset);
  set(openDialog, false);
}

// How many the chain holds before the search box narrows it, so the count can read "12 of 836".
const totalForChain = computed<number>(() => {
  const selected = get(internalChain);
  if (selected === ALL_CHAINS) {
    const allowed = new Set(get(supportedChainsForConnectedAccount));
    return get(orderedAssets).filter(option => allowed.has(option.asset.chain)).length;
  }
  return get(orderedAssets).filter(option => option.asset.chain === selected).length;
});

const { highlight, highlighted, onKeydown, onPointerMove } = useTradeAssetNavigation(assetOptions, {
  onClose: () => set(openDialog, false),
  onSelect: (option: TradeAssetOption) => selectAsset(option.asset),
  scrollTo,
});

function setMax() {
  emit('set-max');
}

// Both halves, not just the identifier: a native token id is shared across chains, so comparing on
// the identifier alone ticks the ETH row of every chain at once.
function isSelected(option: TradeAssetOption): boolean {
  return option.asset.asset === get(asset) && option.asset.chain === get(chain);
}

/**
 * Keeps the selection valid for the chain in play.
 *
 * This was two overlapping `watchImmediate` blocks that both assigned `asset`, one of which also
 * assigned `chain` and so re-triggered the other. One watcher covers both cases: with a chain, hold
 * the selection if it is still owned there and otherwise take the head of that chain's list; with
 * no chain, take the head of the whole list, which is already ordered native-first.
 */
watchImmediate([() => address, chain, orderedAssets], ([, currentChain]) => {
  // Drawn from the display order, not from the raw owned list: picking the default off a different
  // ordering than the dialog shows meant the form opened on an asset nowhere near the top of the
  // list the user then saw.
  const owned = get(orderedAssets);

  if (!currentChain) {
    const first = owned[0];
    if (first) {
      set(asset, first.asset.asset);
      set(chain, first.asset.chain);
    }
    return;
  }

  const ownedOnChain = owned.filter(option => option.asset.chain === currentChain);
  if (ownedOnChain.length === 0)
    return;

  const currentAsset = get(asset);
  if (!currentAsset || !ownedOnChain.some(option => option.asset.asset === currentAsset)) {
    set(asset, ownedOnChain[0].asset.asset);
  }
});

watchImmediate(chain, (chainVal: string) => {
  set(internalChain, chainVal);
});

// A stale query would otherwise hide the list the next time the dialog opens.
watch(openDialog, async (open) => {
  if (!open) {
    set(search, '');
    return;
  }
  set(namesNeeded, true);
  await nextTick();
  get(searchField)?.focus();
  // Opens on what is currently selected rather than at the top, so the active asset is both visible
  // and the row Enter would commit.
  highlight(get(asset), get(chain));
});

const { detectTokens: orchestratorDetect } = useTokenDetectionOrchestrator();

function redetectTokens(): void {
  const chain = get(internalChain);
  const addressVal = address;

  if (addressVal && chain) {
    startPromise(orchestratorDetect(chain, [addressVal]));
  }
}
</script>

<template>
  <div
    class="border border-default rounded-b-lg bg-rui-grey-50 dark:bg-rui-grey-900 px-3 py-2.5 mt-0.5 flex justify-between items-center hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800 cursor-pointer gap-4"
    @click="openDialog = true"
  >
    <TradeAssetDisplay
      v-if="asset && assetDetail"
      :key="asset + chain"
      class="py-2 -my-2 flex-1 overflow-hidden"
      :data="assetDetail"
      :amount="amount"
      @refresh="emit('refresh')"
    />
    <div
      v-else
      class="h-9 text-rui-text-secondary flex items-center"
    >
      {{ t('trade.select_asset.title') }}
    </div>
    <div class="flex items-center gap-2 text-rui-text-secondary">
      <RuiButton
        v-if="connected"
        class="rounded-full"
        size="sm"
        color="primary"
        @click.stop="setMax()"
      >
        {{ t('trade.select_asset.max') }}
      </RuiButton>
      <RuiIcon
        name="lu-chevron-down"
        size="20"
      />
    </div>
  </div>
  <RuiDialog
    v-model="openDialog"
    max-width="500"
  >
    <RuiCard
      divide
      no-padding
      content-class="overflow-hidden"
    >
      <template #header>
        {{ t('trade.select_asset.select_token') }}
      </template>
      <!-- No colour override: `text-white` painted the icon white on the card's white header, so
           the close button was invisible in light mode. The button's own colour handles both
           themes. -->
      <RuiButton
        variant="text"
        class="absolute top-2 right-2"
        icon
        :aria-label="t('common.actions.close')"
        data-testid="trade-asset-close"
        @click="openDialog = false"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
      <div class="p-4 pb-4">
        <RuiAlert
          v-if="useQueryingBalances"
          class="mb-4"
          type="warning"
        >
          {{ t('trade.warning.query_on_progress') }}
        </RuiAlert>
        <div class="flex gap-2 items-center">
          <ChainSelect
            v-model="internalChain"
            class="flex-1"
            hide-details
            dense
            :items="chainOptions"
          />
          <RuiTooltip
            :open-delay="400"
            :popper="{ placement: 'top' }"
          >
            <template #activator>
              <RuiButton
                variant="text"
                icon
                class="!p-1"
                color="primary"
                :disabled="!address || !internalChain"
                :loading="useQueryingBalances || isDetecting"
                @click="redetectTokens()"
              >
                <RuiIcon name="lu-refresh-ccw" />
              </RuiButton>
            </template>
            {{ t('account_balances.detect_tokens.tooltip.redetect') }}
          </RuiTooltip>
        </div>
        <div class="flex items-center gap-2 mt-2 px-3 border rounded-md transition-colors border-default focus-within:border-rui-primary">
          <RuiIcon
            name="lu-search"
            size="16"
            class="text-rui-text-secondary shrink-0"
            aria-hidden="true"
          />
          <input
            ref="searchField"
            v-model="search"
            type="text"
            class="flex-1 min-w-0 bg-transparent py-2 text-sm text-rui-text-primary outline-none placeholder:text-rui-text-secondary"
            :placeholder="t('trade.select_asset.search')"
            :aria-label="t('trade.select_asset.search')"
            autocomplete="off"
            spellcheck="false"
            role="combobox"
            aria-controls="trade-asset-listbox"
            :aria-expanded="assetOptions.length > 0"
            :aria-activedescendant="assetOptions.length > 0 ? `trade-asset-option-${highlighted}` : undefined"
            data-testid="trade-asset-search"
            @keydown="onKeydown($event)"
          />
          <RuiButton
            v-if="search"
            variant="text"
            icon
            size="sm"
            class="!p-1 shrink-0"
            :aria-label="t('common.actions.clear')"
            data-testid="trade-asset-search-clear"
            @click="search = ''"
          >
            <RuiIcon
              name="lu-x"
              size="14"
            />
          </RuiButton>
        </div>
        <!-- The list is a fixed height, so how much sits below the fold is not otherwise visible. -->
        <div
          class="mt-2 text-xs text-rui-text-secondary"
          aria-live="polite"
          data-testid="trade-asset-count"
        >
          {{ search
            ? t('trade.select_asset.result_count', { count: assetOptions.length, total: totalForChain })
            : t('trade.select_asset.asset_count', { count: assetOptions.length }, assetOptions.length) }}
        </div>
      </div>
      <!-- Virtualized: a single chain can carry well over a hundred owned assets, and every row
           mounts an icon plus its asset resolution. -->
      <!-- A fixed height, not a max: the list is searched, and sizing to the result count makes the
           dialog grow and collapse on every keystroke. Viewport-relative so it still fits a short
           window, but never content-relative. -->
      <div
        v-if="assetOptions.length > 0"
        v-bind="containerProps"
        id="trade-asset-listbox"
        role="listbox"
        class="h-[min(24rem,50vh)] pb-2"
      >
        <div v-bind="wrapperProps">
          <button
            v-for="{ data: option, index } in list"
            :id="`trade-asset-option-${index}`"
            :key="option.asset.asset + option.asset.chain"
            type="button"
            role="option"
            class="w-full text-left cursor-pointer py-2 px-4 focus-visible:outline-none"
            :class="index === highlighted
              ? 'bg-rui-primary/10'
              : 'hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800'"
            :style="{ height: `${ITEM_HEIGHT}px` }"
            :aria-selected="isSelected(option)"
            data-testid="trade-asset-option"
            :data-key="option.asset.asset"
            :data-chain="option.asset.chain"
            @mousemove="onPointerMove($event, index)"
            @click="selectAsset(option.asset)"
          >
            <TradeAssetDisplay
              list
              :data="option.asset"
              :symbol="option.symbol"
              :name="option.name"
              :address="option.ambiguous ? option.address : ''"
              :selected="isSelected(option)"
            />
          </button>
        </div>
      </div>
      <!-- Same height as the populated list, so searching down to nothing does not collapse the
           dialog around the search box the user is still typing in. -->
      <!-- Keeps the id the search field's aria-controls names, so it does not dangle when the list
           is empty. -->
      <div
        v-else
        id="trade-asset-listbox"
        class="h-[min(24rem,50vh)] px-4 flex items-center justify-center text-center text-rui-text-secondary"
        role="status"
        aria-live="polite"
        data-testid="trade-asset-empty"
      >
        {{ search ? t('trade.select_asset.no_search_results', { query: search }) : t('trade.select_asset.no_assets_found') }}
      </div>
    </RuiCard>
  </RuiDialog>
</template>
