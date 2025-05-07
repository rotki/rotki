<script setup lang="ts">
import type { AssetInfoWithId } from '@/types/asset';
import type { NftAsset } from '@/types/nfts';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { uniqueObjects } from '@/utils/data';
import { assert, getValidSelectorFromEvmAddress, transformCase } from '@rotki/common';
import { CanceledError } from 'axios';

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<string | undefined>({ required: true });

const props = withDefaults(defineProps<{
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
  asset?: AssetInfoWithId | NftAsset;
}>(), {
  asset: undefined,
  clearable: false,
  disabled: false,
  errorMessages: () => [],
  excludes: () => [],
  hideDetails: false,
  hint: '',
  includeNfts: false,
  items: () => [],
  label: 'Asset',
  outlined: false,
  required: false,
  showIgnored: false,
  successMessages: '',
});

const emit = defineEmits<{
  'update:asset': [value?: AssetInfoWithId | NftAsset];
}>();

defineSlots<{
  prepend: () => any;
}>();

const { errorMessages, excludes, includeNfts, items, showIgnored } = toRefs(props);
const { useIsAssetIgnored } = useIgnoredAssetsStore();

const search = ref<string>('');
const assets = ref<(AssetInfoWithId | NftAsset)[]>([]);
const error = ref('');
const loading = ref(false);
let pending: AbortController | null = null;

const { assetMapping, assetSearch } = useAssetInfoApi();
const { t } = useI18n({ useScope: 'global' });

const errors = computed(() => {
  const messages = [...get(errorMessages)];
  const errorMessage = get(error);
  if (errorMessage)
    messages.unshift(errorMessage);

  return messages;
});

const visibleAssets = computed<AssetInfoWithId[]>(() => {
  const itemsVal = get(items);
  const excludesVal = get(excludes);
  const knownAssets = get(assets);

  const includeIgnored = get(showIgnored);
  const filtered = knownAssets.filter(({ identifier }: AssetInfoWithId) => {
    const unIgnored = includeIgnored || !get(useIsAssetIgnored(identifier));

    const included = itemsVal && itemsVal.length > 0 ? itemsVal.includes(identifier) : true;

    const excluded
      = excludesVal && excludesVal.length > 0
        ? excludesVal.some(excludedId => identifier.toLowerCase() === excludedId?.toLowerCase())
        : false;

    return !!identifier && unIgnored && included && !excluded;
  });

  return uniqueObjects<AssetInfoWithId>(filtered, item => item.identifier);
});

async function searchAssets(keyword: string, signal: AbortSignal): Promise<void> {
  set(loading, true);
  try {
    const fetchedAssets = await assetSearch({
      limit: 50,
      searchNfts: get(includeNfts),
      signal,
      value: keyword,
    });
    if (get(modelValue))
      await retainSelectedValueInOptions(fetchedAssets);
    else set(assets, fetchedAssets);

    pending = null;
    set(loading, false);
  }
  catch (error_: any) {
    if (!(error_ instanceof CanceledError)) {
      set(loading, false);
      set(error, error_.message);
    }
  }
}

function getVisibleAsset(identifier: string) {
  return get(visibleAssets)?.find(asset => asset.identifier === identifier);
}

function onUpdateModelValue(value: string) {
  set(modelValue, value);
  emit('update:asset', getVisibleAsset(value));
}

async function retainSelectedValueInOptions(newAssets: (AssetInfoWithId | NftAsset)[]) {
  try {
    const val = get(modelValue);
    assert(val);
    const mapping = await assetMapping([val]);
    set(assets, [
      ...newAssets,
      {
        identifier: val,
        ...mapping.assets[transformCase(val, true)],
      },
    ]);
  }
  catch (error_: any) {
    set(loading, false);
    set(error, error_.message);
  }
}

async function checkValue() {
  if (!get(modelValue))
    return;

  await retainSelectedValueInOptions(get(assets));
}

watch(modelValue, async () => {
  await checkValue();
});

watch(search, (search) => {
  if (search)
    set(loading, true);
  else if (!pending)
    set(loading, false);
});

watchDebounced(search, async (search) => {
  if (!search)
    return set(loading, false);

  if (pending) {
    pending.abort();
    pending = null;
  }
  set(error, '');
  pending = new AbortController();
  await searchAssets(search, pending.signal);
}, { debounce: 800 });

watch(visibleAssets, () => {
  const identifier = get(modelValue);
  if (identifier && !getVisibleAsset(identifier))
    onUpdateModelValue('');
});

onMounted(async () => {
  await checkValue();
});

onUnmounted(() => {
  if (!isDefined(pending)) {
    return;
  }
  get(pending).abort();
});
</script>

<template>
  <RuiAutoComplete
    v-model="modelValue"
    v-model:search-input="search"
    :disabled="disabled"
    :options="visibleAssets"
    class="asset-select w-full [&_.group]:py-1.5"
    menu-class="!min-w-full"
    :hint="hint"
    :label="label"
    :clearable="clearable"
    :required="required"
    :success-messages="successMessages"
    :error-messages="errors"
    key-attr="identifier"
    text-attr="identifier"
    :hide-details="hideDetails"
    :hide-no-data="loading || !search || !!error"
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
          class="py-0 pl-1"
          :asset="item"
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
        class="py-0 -my-1"
        :asset="item"
      />
    </template>
    <template #no-data>
      <div
        data-cy="no_assets"
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
