<script setup lang="ts">
import { type Ref, useListeners } from 'vue';
import { type AssetInfoWithId } from '@/types/asset';
import { transformCase } from '@/utils/text';
import { type NftAsset } from '@/types/nfts';
import { getValidSelectorFromEvmAddress } from '@/utils/assets';

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
    includeNfts: false
  }
);

const emit = defineEmits<{ (e: 'input', value: string): void }>();

const { items, showIgnored, excludes, errorMessages, value, includeNfts } =
  toRefs(props);
const { isAssetIgnored } = useIgnoredAssetsStore();

const input = (value: string) => {
  emit('input', value || '');
};

const autoCompleteInput = ref(null);
const search = ref<string>('');
const assets: Ref<(AssetInfoWithId | NftAsset)[]> = ref([]);
const error = ref('');
const loading = ref(false);

const { assetSearch, assetMapping } = useAssetInfoApi();
const { t } = useI18n();

const errors = computed(() => {
  const messages = get(errorMessages);
  const errorMessage = get(error);
  if (errorMessage) {
    messages.push(errorMessage);
  }
  return messages;
});

const visibleAssets = computed<AssetInfoWithId[]>(() => {
  const itemsVal = get(items);
  const excludesVal = get(excludes);
  const knownAssets = get(assets);

  const includeIgnored = get(showIgnored);
  return knownAssets.filter((asset: AssetInfoWithId) => {
    const unIgnored = includeIgnored || !get(isAssetIgnored(asset.identifier));

    const included =
      itemsVal && itemsVal.length > 0
        ? itemsVal.includes(asset.identifier)
        : true;

    const excluded =
      excludesVal && excludesVal.length > 0
        ? excludesVal.includes(asset.identifier)
        : false;

    return !!asset.identifier && unIgnored && included && !excluded;
  });
});

const assetText = (asset: AssetInfoWithId): string =>
  `${asset.symbol} ${asset.name}`;

const blur = () => {
  useTimeoutFn(() => {
    set(search, '');
  }, 200);
};

const searchAssets = async (
  keyword: string,
  signal: AbortSignal
): Promise<void> => {
  try {
    set(assets, await assetSearch(keyword, 50, get(includeNfts), signal));
  } catch (e: any) {
    set(error, e.message);
  }
};

let pending: AbortController | null = null;

watch(search, search => {
  if (search) {
    set(loading, true);
  } else {
    set(loading, false);
  }
});

watchThrottled(
  search,
  async search => {
    if (!search) {
      return;
    }
    if (pending) {
      pending.abort();
      pending = null;
    }
    set(error, '');
    set(loading, true);
    const controller = new AbortController();
    pending = controller;
    await searchAssets(search, controller.signal);
    set(loading, false);
  },
  {
    throttle: 800
  }
);

const checkValue = async () => {
  const val = get(value);
  if (!val) {
    return;
  }
  const mapping = await assetMapping([val]);
  set(assets, [
    ...get(assets),
    {
      identifier: val,
      ...mapping.assets[transformCase(val, true)]
    }
  ]);
};

onMounted(async () => {
  await checkValue();
});

watch(value, async () => {
  await checkValue();
});

const listeners = useListeners();
</script>

<template>
  <VAutocomplete
    ref="autoCompleteInput"
    :value="value"
    :disabled="disabled"
    :items="visibleAssets"
    class="asset-select"
    :hint="hint"
    :label="label"
    :clearable="clearable"
    :persistent-hint="persistentHint"
    :required="required"
    :success-messages="successMessages"
    :error-messages="errors"
    item-value="identifier"
    :search-input.sync="search"
    :item-text="assetText"
    :hide-details="hideDetails"
    :hide-no-data="loading || !search"
    auto-select-first
    :loading="loading"
    :menu-props="{ closeOnContentClick: true }"
    :outlined="outlined"
    no-filter
    :class="outlined ? 'asset-select--outlined' : null"
    v-on="listeners"
    @input="input($event)"
    @blur="blur()"
  >
    <template #selection="{ item }">
      <template v-if="item && item.identifier">
        <NftDetails
          v-if="item.assetType === 'nft'"
          :identifier="item.identifier"
          size="40px"
          class="overflow-hidden"
        />
        <AssetDetailsBase v-else class="asset-select__details" :asset="item" />
      </template>
    </template>
    <template #item="{ item }">
      <NftDetails
        v-if="item.assetType === 'nft'"
        :identifier="item.identifier"
        size="40px"
        class="overflow-hidden"
      />
      <AssetDetailsBase
        v-else
        :id="`asset-${getValidSelectorFromEvmAddress(
          item.identifier.toLocaleLowerCase()
        )}`"
        class="asset-select__details"
        :asset="item"
      />
    </template>
    <template #no-data>
      <div data-cy="no_assets" class="px-4 py-2">
        {{ t('asset_select.no_results') }}
      </div>
    </template>
    <template #append>
      <div v-if="loading" class="h-full flex items-center">
        <RuiProgress
          class="asset-select__loading"
          color="primary"
          variant="indeterminate"
          circular
          thickness="3"
          size="30"
        />
      </div>
    </template>
    <template #prepend>
      <slot name="prepend" />
    </template>
  </VAutocomplete>
</template>

<style scoped lang="scss">
.asset-select {
  &__details {
    padding-top: 4px;
    padding-bottom: 4px;
  }

  &__loading {
    margin-top: -2px;
  }

  &--outlined {
    /* stylelint-disable selector-class-pattern,selector-nested-pattern */

    :deep(.v-select__slot) {
      /* stylelint-enable selector-class-pattern,selector-nested-pattern */

      .v-input {
        &__icon {
          &--append {
            i {
              bottom: 10px;
            }
          }

          &--clear {
            button {
              bottom: 10px;
            }
          }
        }
      }
    }
  }

  /* stylelint-disable selector-class-pattern,selector-nested-pattern */

  :deep(.v-select__slot) {
    /* stylelint-enable selector-class-pattern,selector-nested-pattern */
    height: 56px;
    margin-top: -2px;

    .v-label {
      top: 20px;
    }

    .v-input {
      &__icon {
        padding-top: 20px;
      }
    }

    .v-select {
      &__selections {
        margin-top: 4px;
        display: flex;
        flex-flow: nowrap;
      }
    }
  }
}
</style>
