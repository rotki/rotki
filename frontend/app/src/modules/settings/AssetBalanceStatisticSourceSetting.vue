<script setup lang="ts">
/**
 * The balance source in a menu of its own.
 *
 * @remarks
 * Kept for premium bundles that predate `StatisticsGraphSettings`' `source` prop; newer ones offer
 * the source in that one menu.
 */
import AssetBalanceSourceOptions from '@/modules/settings/AssetBalanceSourceOptions.vue';
import { useAssetBalanceSourceSetting } from '@/modules/settings/use-asset-balance-source-setting';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';

const { asset } = defineProps<{
  asset?: string;
}>();

const emit = defineEmits<{
  preference: [preference?: 'events' | 'snapshot'];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  modelUseHistoricalAssetBalances,
  name,
  persistSource,
  rememberStateForAsset,
} = useAssetBalanceSourceSetting(() => asset, preference => emit('preference', preference));
</script>

<template>
  <RuiMenu
    :class-names="{ menu: 'min-w-72 max-w-80' }"
    :options="{ placement: 'top' }"
  >
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="t('statistics_graph_settings.source.title')"
        class-name="graph-period"
        custom-color
        v-bind="attrs"
      >
        <RuiIcon name="lu-file-cog" />
      </MenuTooltipButton>
    </template>

    <AssetBalanceSourceOptions
      v-model:source="modelUseHistoricalAssetBalances"
      v-model:remember="rememberStateForAsset"
      class="p-4"
      :asset="asset"
      :name="name"
      @update:source="persistSource($event)"
    />
  </RuiMenu>
</template>
