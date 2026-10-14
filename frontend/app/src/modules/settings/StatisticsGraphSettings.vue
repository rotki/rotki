<script setup lang="ts">
import AssetBalanceSourceOptions from '@/modules/settings/AssetBalanceSourceOptions.vue';
import InferZeroTimedBalancesSetting from '@/modules/settings/InferZeroTimedBalancesSetting.vue';
import SsfGraphMultiplierSetting from '@/modules/settings/SsfGraphMultiplierSetting.vue';
import { useAssetBalanceSourceSetting } from '@/modules/settings/use-asset-balance-source-setting';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';

/**
 * The asset graph's settings in one menu. With `source` it also offers where the balances come
 * from, which `AssetBalanceStatisticSourceSetting` offered in a menu of its own.
 */
const { asset, source = false } = defineProps<{
  asset?: string;
  source?: boolean;
}>();

const emit = defineEmits<{
  updated: [];
  preference: [preference?: 'events' | 'snapshot'];
}>();

const { t } = useI18n({ useScope: 'global' });

const showMenu = ref<boolean>(false);

const {
  modelUseHistoricalAssetBalances,
  name,
  persistSource,
  rememberStateForAsset,
} = useAssetBalanceSourceSetting(() => asset, preference => emit('preference', preference), () => source);

const updated = (): void => emit('updated');
</script>

<template>
  <RuiMenu
    v-model="showMenu"
    :class-names="{ menu: 'w-80 max-h-[calc(100vh-8rem)] overflow-y-auto' }"
    :options="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="t('statistics_graph_settings.tooltip')"
        class-name="graph-period"
        custom-color
        v-bind="attrs"
      >
        <RuiIcon name="lu-sliders-horizontal" />
      </MenuTooltipButton>
    </template>

    <div class="flex flex-col p-4 between:border-t between:border-rui-divider between:mt-4 between:pt-4">
      <AssetBalanceSourceOptions
        v-if="source"
        v-model:source="modelUseHistoricalAssetBalances"
        v-model:remember="rememberStateForAsset"
        :asset="asset"
        :name="name"
        @update:source="persistSource($event)"
      />
      <SsfGraphMultiplierSetting @updated="updated()" />
      <InferZeroTimedBalancesSetting @updated="updated()" />
    </div>
  </RuiMenu>
</template>
