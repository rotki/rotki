<script setup lang="ts">
import type { NftAsset } from '@/modules/assets/nfts';
import { type AssetInfoWithId, getValidSelectorFromEvmAddress } from '@rotki/common';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import { useAssetSearch } from '@/modules/shell/components/inputs/use-asset-search';

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<string | undefined>({ required: true });

/**
 * The resolved asset behind the selected identifier. The component only ever writes it, so it is a
 * `defineModel` rather than a prop plus a matching emit; `v-model:asset` and the explicit
 * `:asset` + `@update:asset` pair both keep working unchanged.
 */
const asset = defineModel<AssetInfoWithId | NftAsset | undefined>('asset');

const {
  chain,
  clearable = false,
  disabled = false,
  errorMessages = [],
  excludes = [],
  hideDetails = false,
  hint = '',
  includeNfts = false,
  items = [],
  label = 'Asset',
  outlined = false,
  required = false,
  showIgnored = false,
  successMessages = '',
} = defineProps<{
  items?: string[];
  excludes?: string[];
  hint?: string;
  successMessages?: string;
  errorMessages?: string[];
  label?: string;
  disabled?: boolean;
  outlined?: boolean;
  clearable?: boolean;
  required?: boolean;
  showIgnored?: boolean;
  hideDetails?: boolean;
  includeNfts?: boolean;
  chain?: string;
}>();

defineSlots<{
  prepend: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const { error, getVisibleAsset, loading, modelSearch, visibleAssets } = useAssetSearch({
  chain: () => chain,
  excludes: () => excludes,
  includeNfts: () => includeNfts,
  items: () => items,
  modelValue,
  showIgnored: () => showIgnored,
});

const errors = computed<string[]>(() => {
  const messages = [...errorMessages];
  const errorMessage = get(error);
  if (errorMessage)
    messages.unshift(errorMessage);

  return messages;
});

function onUpdateModelValue(value: string): void {
  set(modelValue, value);
  set(asset, getVisibleAsset(value));
}

watch(visibleAssets, (_, oldVisibleAssets) => {
  const identifier = get(modelValue);
  if (!identifier || !oldVisibleAssets)
    return;

  // Only clear if the asset was previously visible and is now not visible
  // This prevents clearing newly selected values that haven't been loaded yet
  const wasVisible = oldVisibleAssets.some(asset => asset.identifier === identifier);
  if (!wasVisible)
    return;

  if (!getVisibleAsset(identifier))
    onUpdateModelValue('');
});
</script>

<template>
  <RuiAutoComplete
    v-model="modelValue"
    v-model:search-input="modelSearch"
    :disabled="disabled"
    :options="visibleAssets"
    class="asset-select w-full [&_.group]:py-1.5"
    menu-class="!min-w-full"
    :hint="hint"
    :label="label"
    :clearable="clearable"
    :placeholder="t('asset_select.placeholder')"
    :required="required"
    :success-messages="successMessages"
    :error-messages="errors"
    key-attr="identifier"
    text-attr="identifier"
    :hide-details="hideDetails"
    :hide-no-data="loading || !modelSearch || !!error"
    auto-select-first
    :loading="loading"
    :variant="outlined ? 'outlined' : 'default'"
    :item-height="50"
    v-bind="$attrs"
    no-filter
  >
    <template #selection="{ item }">
      <template v-if="item && item.identifier">
        <NftDetails
          v-if="item.assetType === 'nft'"
          :identifier="item.identifier"
          size="36px"
          class="overflow-hidden text-sm -my-2"
        />
        <AssetDetailsBase
          v-else
          class="!py-0 pl-1"
          :asset="item"
          hide-menu
        />
      </template>
    </template>
    <template #item="{ item }">
      <NftDetails
        v-if="item.assetType === 'nft'"
        :identifier="item.identifier"
        size="36px"
        class="overflow-hidden text-sm -my-2"
      />
      <AssetDetailsBase
        v-else
        :id="`asset-${getValidSelectorFromEvmAddress(item.identifier.toLocaleLowerCase())}`"
        class="!py-0 -my-1"
        :asset="item"
        hide-menu
      />
    </template>
    <template #no-data>
      <div
        data-testid="no_assets"
        class="p-4"
      >
        {{ t('asset_select.no_results') }}
      </div>
    </template>
    <template #selection.prepend>
      <slot name="prepend" />
    </template>
  </RuiAutoComplete>
</template>
