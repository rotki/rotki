<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { TradableAsset } from '@/modules/wallet/types';
import { FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

const { data, symbol: providedSymbol, name: providedName } = defineProps<{
  data: TradableAsset;
  list?: boolean;
  amount?: BigNumber;
  /** Pre-resolved symbol. The option list resolves once per asset, so rows need not resolve again. */
  symbol?: string;
  /** Pre-resolved name, as above. */
  name?: string;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { useAssetField } = useAssetInfoRetrieval();
const { getEvmChainName } = useSupportedChains();

const resolvedSymbol = useAssetField(() => data.asset, 'symbol', { collectionParent: false });
const resolvedName = useAssetField(() => data.asset, 'name', { collectionParent: false });

// Short-circuits, so a provided value leaves the resolution computed unevaluated rather than
// merely unused: `computed` is lazy, and nothing else reads these.
const symbol = computed<string>(() => providedSymbol ?? get(resolvedSymbol));
const name = computed<string>(() => providedName ?? get(resolvedName));
</script>

<template>
  <div class="flex gap-2 items-center">
    <AssetDetails
      :asset="data.asset"
      :display="{ iconOnly: true, size: '32px' }"
      :actions="{ hideActions: true }"
      :resolution="{
        forceChain: getEvmChainName(data.chain) || undefined,
        options: { collectionParent: false },
      }"
    />
    <div
      class="truncate gap-4"
      :class="{
        'w-full flex items-center justify-between': list,
      }"
    >
      <div class="font-medium text-sm -mb-0.5 overflow-hidden truncate">
        <div class="truncate">
          {{ symbol }}
        </div>
        <div
          v-if="list || !(data.price && data.fiatValue)"
          class="truncate text-rui-text-secondary font-normal"
        >
          {{ name }}
        </div>
      </div>
      <div
        v-if="!list && data.price"
        class="text-sm text-rui-text flex items-center gap-1 whitespace-nowrap"
      >
        <span>{{ t('trade.select_asset.balance') }}:</span>
        <RuiSkeletonLoader
          v-if="!amount"
          class="w-28 flex"
        />

        <template v-else>
          <div>
            <ValueDisplay
              :value="amount"
              no-scramble
            />
          </div>
          <div>
            (<FiatDisplay
              no-scramble
              :value="data.price.multipliedBy(amount)"
            />)
          </div>
          <div>
            <RuiButton
              icon
              variant="text"
              size="sm"
              class="!p-1"
              @click.stop="emit('refresh')"
            >
              <RuiIcon
                name="lu-refresh-ccw"
                size="12"
              />
            </RuiButton>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
