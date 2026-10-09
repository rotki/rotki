<script lang="ts" setup>
import type { AssetBalance } from '@rotki/common';
import type { AssetResolutionOptions } from '@/modules/assets/use-asset-info-retrieval';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import { useSetting } from '@/modules/settings/use-setting';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';

const { assets, visible = 3 } = defineProps<{
  assets: AssetBalance[];
  visible?: number;
  resolutionOptions?: AssetResolutionOptions;
  showChain?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const shouldShowAmount = useSetting('shouldShowAmount');
/** The assets past the icons, shown as "+N" like the chains column; the total is its label. */
const hidden = computed<number>(() => Math.max(0, assets.length - visible));
const router = useRouter();

async function navigateToAsset(asset: AssetBalance): Promise<void> {
  await router.push({
    name: '/assets/[identifier]',
    params: {
      identifier: asset.asset,
    },
  });
}
</script>

<template>
  <!--
    The top assets by value as small bare icons, overlapping with a ring in the surface colour so
    each stays whole, then the total as plain text rather than a bubble.
  -->
  <div class="flex items-center justify-end">
    <div class="flex items-center pl-1.5">
      <template
        v-for="asset in assets.slice(0, visible)"
        :key="asset.asset"
      >
        <RuiTooltip
          :disabled="!shouldShowAmount"
          :close-delay="0"
          :class-names="{ tooltip: '-ml-1!' }"
        >
          <template #activator>
            <div
              data-testid="top-asset"
              class="rounded-full size-6 flex items-center justify-center bg-rui-surface ring-2 ring-rui-surface -ml-1.5 cursor-pointer"
              @click="navigateToAsset(asset)"
            >
              <AssetIcon
                no-tooltip
                flat
                :identifier="asset.asset"
                :resolution-options="resolutionOptions"
                size="24px"
                padding="0px"
                class="[&_.icon-bg]:rounded-full! [&_.icon-bg]:overflow-hidden!"
                :show-chain="showChain"
              />
            </div>
          </template>

          <AssetAmountDisplay
            :asset="asset.asset"
            :amount="asset.amount"
            :no-collection-parent="!resolutionOptions?.collectionParent"
            data-testid="top-asset-amount"
          />
        </RuiTooltip>
      </template>
    </div>

    <!-- a fixed slot, start-aligned, so the icons line up down the column whatever the count's width -->
    <span class="ml-1.5 min-w-8 text-xs font-medium text-rui-text-secondary tabular-nums whitespace-nowrap">
      <span
        v-if="hidden > 0"
        :title="t('account_balances.asset_count', { count: assets.length }, assets.length)"
        :aria-label="t('account_balances.asset_count', { count: assets.length }, assets.length)"
        data-testid="top-asset-count"
      >
        +{{ hidden }}
      </span>
    </span>
  </div>
</template>
