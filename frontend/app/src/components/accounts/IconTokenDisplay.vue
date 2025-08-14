<script lang="ts" setup>
import type { AssetBalance } from '@rotki/common';
import type { AssetResolutionOptions } from '@/composables/assets/retrieval';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const props = withDefaults(defineProps<{
  assets: AssetBalance[];
  loading: boolean;
  visible?: number;
  resolutionOptions?: AssetResolutionOptions;
  showChain?: boolean;
}>(), {
  resolutionOptions: () => ({ collectionParent: false }),
  showChain: false,
  visible: 3,
});

const { assets, visible } = toRefs(props);
const { shouldShowAmount } = storeToRefs(useFrontendSettingsStore());
const showMore = computed<number>(() => get(assets).length - get(visible));
const router = useRouter();

async function navigateToAsset(asset: AssetBalance) {
  await router.push({
    name: '/assets/[identifier]',
    params: {
      identifier: asset.asset,
    },
  });
}
</script>

<template>
  <div class="flex justify-end pl-2">
    <template
      v-for="asset in assets.slice(0, visible)"
      :key="asset.asset"
    >
      <RuiTooltip
        :disabled="!shouldShowAmount"
        :close-delay="0"
        tooltip-class="!-ml-1"
      >
        <template #activator>
          <div
            data-cy="top-asset"
            class="rounded-full size-8 flex items-center justify-center border bg-white border-rui-grey-300 dark:border-rui-grey-700 -ml-2 cursor-pointer"
            @click="navigateToAsset(asset)"
          >
            <AssetIcon
              no-tooltip
              flat
              :identifier="asset.asset"
              :resolution-options="resolutionOptions"
              size="30px"
              padding="1px"
              class="[&_.icon-bg]:!rounded-full [&_.icon-bg]:!overflow-hidden [&_.icon-bg]:p-[1px]"
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
