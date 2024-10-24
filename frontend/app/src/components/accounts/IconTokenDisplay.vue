<script lang="ts" setup>
import type { AssetResolutionOptions } from '@/composables/assets/retrieval';
import type { AssetBalance } from '@/types/balances';

const props = withDefaults(defineProps<{
  assets: AssetBalance[];
  loading: boolean;
  visible?: number;
  resolutionOptions?: AssetResolutionOptions;
  showChain?: boolean;
}>(), {
  visible: 3,
  resolutionOptions: () => ({ collectionParent: false }),
  showChain: false,
});

const { assets, visible } = toRefs(props);

const showMore = computed<number>(() => get(assets).length - get(visible));
</script>

<template>
  <div class="flex justify-end pl-2">
    <template
      v-for="asset in assets.slice(0, visible)"
      :key="asset.asset"
    >
      <RuiTooltip
        :close-delay="0"
        tooltip-class="!-ml-1"
      >
        <template #activator>
          <div
            data-cy="top-asset"
            class="rounded-full w-8 h-8 bg-rui-grey-300 dark:bg-white flex items-center justify-center border-2 border-white dark:border-rui-grey-300 -ml-2 cursor-pointer"
          >
            <AssetIcon
              no-tooltip
              flat
              :identifier="asset.asset"
              :resolution-options="resolutionOptions"
              size="24px"
              class="[&_.icon-bg]:!rounded-full [&_.icon-bg]:!overflow-hidden"
              :show-chain="showChain"
            />
          </div>
        </template>

        <AmountDisplay
          :value="asset.amount"
          :asset="asset.asset"
          :asset-padding="0.1"
          :resolution-options="resolutionOptions"
          data-cy="top-asset-amount"
        />
      </RuiTooltip>
    </template>

    <div
      v-if="showMore > 0"
      class="rounded-full h-8 px-1 min-w-8 bg-rui-grey-300 dark:bg-white flex items-center justify-center border-2 border-white dark:border-rui-grey-300 -ml-2 font-bold text-xs text-rui-light-text z-[1]"
    >
      {{ showMore }}+
    </div>
  </div>
</template>
