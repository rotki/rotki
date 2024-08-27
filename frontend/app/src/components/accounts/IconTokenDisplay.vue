<script lang="ts" setup>
import type { AssetBalance } from '@rotki/common';
import type { AssetResolutionOptions } from '@/composables/assets/retrieval';

const props = withDefaults(defineProps<{
  assets: AssetBalance[];
  loading: boolean;
  visible?: number;
  resolutionOptions?: AssetResolutionOptions;
}>(), {
  visible: 3,
  resolutionOptions: () => ({ collectionParent: false }),
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
            class="rounded-full w-8 h-8 bg-rui-grey-300 dark:bg-white flex items-center justify-center border-2 border-white dark:border-rui-grey-300 -ml-2 cursor-pointer overflow-hidden"
          >
            <AssetIcon
              no-tooltip
              flat
              :identifier="asset.asset"
              :resolution-options="resolutionOptions"
              size="24px"
              class="[&_.icon-bg>div]:!rounded-full [&_.icon-bg>div]:!overflow-hidden"
              :show-chain="false"
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
