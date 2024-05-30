<script setup lang="ts">
import { CanceledError } from 'axios';
import { getValidSelectorFromEvmAddress } from '@/utils/assets';
import type { AssetInfoWithId } from '@/types/asset';
import type { NftAsset } from '@/types/nfts';

const props = withDefaults(
  defineProps<{
    items?: string[];
    excludes?: string[];
    hint?: string;
    successMessages?: string;
    errorMessages?: string[];
    label?: string;
    value?: string;
    disabled?: boolean;
    outlined?: boolean;
    clearable?: boolean;
    persistentHint?: boolean;
    required?: boolean;
    showIgnored?: boolean;
    hideDetails?: boolean;
    includeNfts?: boolean;
    asset?: AssetInfoWithId | NftAsset;
  }>(),
  {
    items: () => [],
    excludes: () => [],
    hint: '',
    successMessages: '',
    errorMessages: () => [],
    label: 'Asset',
    value: '',
    disabled: false,
    outlined: false,
    clearable: false,
    persistentHint: false,
    required: false,
    showIgnored: false,
    hideDetails: false,
    includeNfts: false,
    asset: undefined,
  },
);

const emit = defineEmits<{ (e: 'input', value: string): void; (e: 'update:asset', value?: AssetInfoWithId | NftAsset): void }>();

const { items, showIgnored, excludes, errorMessages, value, includeNfts }
  = toRefs(props);
const { isAssetIgnored } = useIgnoredAssetsStore();

const search = ref<string>('');
const assets: Ref<(AssetInfoWithId | NftAsset)[]> = ref([]);
const error = ref('');
const loading = ref(false);
let pending: AbortController | null = null;

const { assetSearch, assetMapping } = useAssetInfoApi();
const { t } = useI18n();

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
    const unIgnored = includeIgnored || !get(isAssetIgnored(identifier));

    const included
      = itemsVal && itemsVal.length > 0
        ? itemsVal.includes(identifier)
        : true;

    const excluded
      = excludesVal && excludesVal.length > 0
        ? excludesVal.some(excludedId => identifier.toLowerCase() === excludedId?.toLowerCase())
        : false;

    return !!identifier && unIgnored && included && !excluded;
  });

  return uniqueObjects<AssetInfoWithId>(filtered, item => item.identifier);
});

function blur() {
  useTimeoutFn(() => {
    set(search, '');
  }, 200);
}

async function searchAssets(keyword: string, signal: AbortSignal): Promise<void> {
  set(loading, true);
  try {
    set(assets, await assetSearch(keyword, 50, get(includeNfts), signal));
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

function input(value: string) {
  emit('input', value || '');
  emit('update:asset', getVisibleAsset(value));
}

watch(search, (search) => {
  if (search)
    set(loading, true);
  else if (!pending)
    set(loading, false);
});

watchDebounced(
  search,
  async (search) => {
    if (!search)
      return set(loading, false);

    if (pending) {
      pending.abort();
      pending = null;
    }
    set(error, '');
    pending = new AbortController();
    await searchAssets(search, pending.signal);
  },
  {
    debounce: 800,
  },
);

async function checkValue() {
  const val = get(value);
  if (!val)
    return;

  try {
    const mapping = await assetMapping([val]);
    set(assets, [
      ...get(assets),
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

onMounted(async () => {
  await checkValue();
});

watch(value, async () => {
  await checkValue();
});

watch(visibleAssets, () => {
  const identifier = get(value);
  if (identifier && !getVisibleAsset(identifier))
    input('');
});
</script>

<template>
  <RuiAutoComplete
    :value="value"
    :disabled="disabled"
    :options="visibleAssets"
    class="asset-select w-full [&_.group]:py-1.5"
    :hint="hint"
    :label="label"
    :clearable="clearable"
    :required="required"
    :success-messages="successMessages"
    :error-messages="errors"
    key-attr="identifier"
    text-attr="identifier"
    :search-input.sync="search"
    :hide-details="hideDetails"
    :hide-no-data="loading || !search || !!error"
    auto-select-first
    :loading="loading"
    :variant="outlined ? 'outlined' : 'default'"
    :item-height="60"
    no-filter
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
    @input="input($event)"
    @blur="blur()"
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
          class="py-0"
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
        :id="`asset-${getValidSelectorFromEvmAddress(
          item.identifier.toLocaleLowerCase(),
        )}`"
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
    <template #prepend>
      <slot name="prepend" />
    </template>
  </RuiAutoComplete>
</template>
