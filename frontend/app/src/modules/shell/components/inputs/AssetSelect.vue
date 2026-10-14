<script setup lang="ts">
import type { NftAsset } from '@/modules/assets/nfts';
import type { AssetActions, AssetDisplay } from '@/modules/assets/types';
import { type AssetInfoWithId, getValidSelectorFromEvmAddress } from '@rotki/common';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';
import { NftHandling } from '@/modules/assets/nft-handling';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import { type AssetSearchSource, useAssetSearch } from '@/modules/shell/components/inputs/use-asset-search';

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
  clearable = false,
  dense = false,
  disabled = false,
  errorMessages = [],
  hideDetails = false,
  hint = '',
  label,
  required = false,
  source,
  successMessages = '',
} = defineProps<{
  /**
   * Which assets may be picked, as one object rather than five loose props.
   *
   * These are the five the search itself consumes, and it already took them as a single argument;
   * stating them together is also what keeps this component's prop list inside the lint ceiling,
   * which matters here because it is registered globally for the premium bundle, so every prop is
   * part of an external API.
   */
  source?: AssetSearchSource;
  hint?: string;
  successMessages?: string;
  errorMessages?: string[];
  label?: string;
  disabled?: boolean;
  clearable?: boolean;
  required?: boolean;
  hideDetails?: boolean;
  dense?: boolean;
}>();

defineSlots<{
  prepend: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const { error, getVisibleAsset, loading, modelSearch, visibleAssets } = useAssetSearch({
  chain: () => source?.chain,
  excludes: () => source?.excludes ?? [],
  items: () => source?.items ?? [],
  modelValue,
  nftHandling: () => source?.nfts ?? NftHandling.EXCLUDE,
  // A selection that drops out of the options takes the resolved asset with it.
  onSelectionLost: (): void => {
    onUpdateModelValue('');
  },
  showIgnored: () => source?.showIgnored ?? false,
});

const fieldLabel = computed<string>(() => label ?? t('asset_select.label'));

/**
 * With an allow-list the field only filters the listed assets, so it must not invite a contract
 * address the user could never pick.
 */
const placeholder = computed<string>(() => (source?.items?.length ?? 0) > 0
  ? t('asset_select.filter_placeholder')
  : t('asset_select.placeholder'));

/**
 * Shared by both slots, which render the asset without its context menu. Hoisted so this is one
 * stable identity rather than a fresh object per rendered row.
 */
const noMenu: AssetActions = { hideMenu: true };

const itemDisplay = computed<AssetDisplay>(() => ({ dense }));

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
</script>

<template>
  <RuiAutoComplete
    v-model="modelValue"
    v-model:search-input="modelSearch"
    :disabled="disabled"
    :options="visibleAssets"
    class="asset-select w-full"
    :class="{ '[&_.group]:py-1.5': !dense }"
    :class-names="{ menu: 'min-w-full!' }"
    :hint="hint"
    :label="fieldLabel"
    :clearable="clearable"
    :placeholder="placeholder"
    :required="required"
    :success-messages="successMessages"
    :error-messages="errors"
    key-attr="identifier"
    text-attr="identifier"
    :hide-details="hideDetails"
    :hide-no-data="loading || !modelSearch || !!error"
    auto-select-first
    :dense="dense"
    :loading="loading"
    :item-height="dense ? 44 : 50"
    v-bind="$attrs"
    no-filter
  >
    <template #selection="{ item }">
      <template v-if="item && item.identifier">
        <NftDetails
          v-if="item.assetType === 'nft'"
          :identifier="item.identifier"
          :size="dense ? '24px' : '36px'"
          class="overflow-hidden text-sm -my-2"
        />
        <div
          v-else
          class="flex items-center gap-2 min-w-0 pl-1"
        >
          <AssetIcon
            :identifier="item.identifier"
            size="20px"
            show-chain
            flat
          />
          <span class="truncate text-sm text-rui-text">
            {{ item.isCustomAsset ? item.name : item.symbol }}
            <span
              v-if="!dense && !item.isCustomAsset && item.name"
              class="text-rui-text-secondary"
            >
              {{ item.name }}
            </span>
          </span>
        </div>
      </template>
    </template>
    <template #item="{ item }">
      <NftDetails
        v-if="item.assetType === 'nft'"
        :identifier="item.identifier"
        :size="dense ? '28px' : '36px'"
        class="overflow-hidden text-sm -my-2"
      />
      <AssetDetailsBase
        v-else
        :id="`asset-${getValidSelectorFromEvmAddress(item.identifier.toLocaleLowerCase())}`"
        :class="dense ? 'py-0! -my-0.5' : 'py-0! -my-1'"
        :asset="item"
        :display="itemDisplay"
        :actions="noMenu"
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
