<script setup lang="ts" generic="TClear = undefined, TClearable extends boolean = false">
import type { ClearedValue, RuiAutoComplete } from '@rotki/ui-library';
import type { NftAsset } from '@/modules/assets/nfts';
import type { AssetActions, AssetDisplay } from '@/modules/assets/types';
import type { ForwardedProps, UnexportedAutoCompleteProps } from '@/modules/core/common/forwarded-props';
import { type AssetInfoWithId, getValidSelectorFromEvmAddress } from '@rotki/common';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';
import { NftHandling } from '@/modules/assets/nft-handling';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import { toClearedValue } from '@/modules/core/common/cleared-value';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import { type AssetSearchSource, useAssetSearch } from '@/modules/shell/components/inputs/use-asset-search';

interface Props {
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
  /**
   * Shows the clear button, so the update can carry `valueOnClear`.
   *
   * @remarks
   * Typed `& boolean` so the compiler emits a Boolean prop: a bare type parameter compiles to an
   * untyped one, and a bare `clearable` attribute would then arrive as a falsy `''`.
   */
  clearable?: TClearable & boolean;
  /** What clearing writes, `undefined` when not given; `''` keeps a `string` model exact. */
  valueOnClear?: TClear;
  dense?: boolean;
  /** The selected identifier. Not a `defineModel`, since the update is typed apart from the prop. */
  modelValue: string | NoInfer<TClear>;
}

defineOptions({
  inheritAttrs: false,
});

/**
 * The resolved asset behind the selected identifier. The component only ever writes it, so it is a
 * `defineModel` rather than a prop plus a matching emit; `v-model:asset` and the explicit
 * `:asset` + `@update:asset` pair both keep working unchanged.
 */
const asset = defineModel<AssetInfoWithId | NftAsset | undefined>('asset');

const {
  clearable,
  dense = false,
  disabled = false,
  errorMessages = [],
  hint = '',
  label,
  modelValue,
  source,
  successMessages = '',
  valueOnClear,
} = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiAutoComplete<string, AssetInfoWithId>, Props & UnexportedAutoCompleteProps>>();

const emit = defineEmits<{
  'update:model-value': [value: string | ClearedValue<string, TClear, TClearable>];
}>();

defineSlots<{
  prepend?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

/** The identifier the search resolves; a clear value that is not an identifier reads as none. */
const selectedIdentifier = computed<string | undefined>(() => (typeof modelValue === 'string' ? modelValue : undefined));

const { error, getVisibleAsset, loading, modelSearch, visibleAssets } = useAssetSearch({
  chain: () => source?.chain,
  excludes: () => source?.excludes ?? [],
  items: () => source?.items ?? [],
  modelValue: selectedIdentifier,
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

/** A picked or emptied identifier goes up as is; a cleared field sends the caller's `valueOnClear`. */
function onUpdateModelValue(value: string | undefined): void {
  if (value === undefined) {
    emit('update:model-value', toClearedValue<string, TClear, TClearable>(valueOnClear));
    set(asset, undefined);
    return;
  }
  emit('update:model-value', value);
  set(asset, getVisibleAsset(value));
}
</script>

<template>
  <RuiAutoComplete
    v-model:search-input="modelSearch"
    :model-value="selectedIdentifier"
    :disabled="disabled"
    :options="visibleAssets"
    class="asset-select w-full"
    :class="{ '[&_.group]:py-1.5': !dense }"
    :class-names="{ menu: 'min-w-full!' }"
    :hint="hint"
    :label="fieldLabel"
    :clearable="clearable"
    :placeholder="placeholder"
    :success-messages="successMessages"
    :error-messages="errors"
    key-attr="identifier"
    text-attr="identifier"
    :hide-no-data="loading || !modelSearch || !!error"
    auto-select-first
    :dense="dense"
    :loading="loading"
    :item-height="dense ? 44 : 50"
    v-bind="$attrs"
    no-filter
    @update:model-value="onUpdateModelValue($event)"
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
