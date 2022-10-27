<template>
  <v-autocomplete
    ref="autoCompleteInput"
    :value="value"
    :disabled="disabled"
    :items="visibleAssets"
    class="asset-select"
    :hint="hint"
    single-line
    :label="label"
    :rules="rules"
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
    @input="input"
    @blur="blur"
  >
    <template #selection="{ item }">
      <asset-details-base
        v-if="item && item.identifier"
        class="asset-select__details ml-2"
        :asset="item"
      />
    </template>
    <template #item="{ item }">
      <div class="pr-4">
        <v-img
          v-if="item.imageUrl"
          width="40px"
          height="40px"
          contain
          :src="item.imageUrl"
        />
        <asset-icon v-else size="40px" :identifier="item.identifier" />
      </div>
      <v-list-item-content
        :id="`asset-${getValidSelectorFromEvmAddress(
          item.identifier.toLocaleLowerCase()
        )}`"
      >
        <template v-if="!item.isCustomAsset">
          <v-list-item-title class="font-weight-medium">
            {{ item.symbol }}
          </v-list-item-title>
          <v-list-item-subtitle>{{ item.name }}</v-list-item-subtitle>
        </template>
        <template v-else>
          <v-list-item-title class="font-weight-medium">
            {{ item.name }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ item.customAssetType }}
          </v-list-item-subtitle>
        </template>
      </v-list-item-content>
    </template>
    <template #no-data>
      <div data-cy="no_assets" class="px-4 py-2">
        {{ tc('asset_select.no_results') }}
      </div>
    </template>
    <template #append>
      <div v-if="loading" class="fill-height d-flex items-center">
        <v-progress-circular
          class="asset-select__loading"
          color="primary"
          indeterminate
          width="3"
          size="30"
        />
      </div>
    </template>
  </v-autocomplete>
</template>

<script setup lang="ts">
import { PropType, Ref } from 'vue';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useAssetInfoApi } from '@/services/assets/info';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { NftAsset, useNftAssetInfoStore } from '@/store/assets/nft';
import { AssetInfoWithId } from '@/types/assets';
import { getValidSelectorFromEvmAddress } from '@/utils/assets';
import { isNft } from '@/utils/nft';

const props = defineProps({
  items: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  },
  excludes: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  },
  hint: { required: false, type: String, default: '' },
  successMessages: { required: false, type: String, default: '' },
  errorMessages: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  },
  label: { required: false, type: String, default: 'Asset' },
  value: { required: false, type: String, default: '' },
  rules: {
    required: false,
    type: Array as PropType<((v: string) => boolean | string)[]>,
    default: () => []
  },
  disabled: { required: false, type: Boolean, default: false },
  outlined: { required: false, type: Boolean, default: false },
  clearable: { required: false, type: Boolean, default: false },
  persistentHint: { required: false, type: Boolean, default: false },
  required: { required: false, type: Boolean, default: false },
  showIgnored: { required: false, type: Boolean, default: false },
  hideDetails: { required: false, type: Boolean, default: false },
  includeNfts: { required: false, type: Boolean, default: false }
});

const emit = defineEmits<{ (e: 'input', value: string): void }>();

const { items, showIgnored, excludes, errorMessages, value, includeNfts } =
  toRefs(props);
const { isAssetIgnored } = useIgnoredAssetsStore();

const input = (value: string) => emit('input', value || '');

const autoCompleteInput = ref(null);
const search = ref<string>('');
const assets: Ref<(AssetInfoWithId | NftAsset)[]> = ref([]);
const error = ref('');
const loading = ref(false);

const { assetSearch, assetMapping } = useAssetInfoApi();
const { getNftDetails, searchNfts } = useNftAssetInfoStore();
const { tc } = useI18n();

const errors = computed(() => {
  let messages = get(errorMessages);
  let errorMessage = get(error);
  if (errorMessage) {
    messages.push(errorMessage);
  }
  return messages;
});

const visibleAssets = computed<AssetInfoWithId[]>(() => {
  const itemsVal = get(items);
  const excludesVal = get(excludes);
  let knownAssets = get(assets);

  let includeIgnored = get(showIgnored);
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

const assetText = (asset: AssetInfoWithId): string => {
  return `${asset.symbol} ${asset.name}`;
};

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
    const allAssets = await assetSearch(keyword, 50, signal);
    if (get(includeNfts)) {
      const nftAssets = searchNfts(keyword);
      set(assets, [...allAssets, ...nftAssets]);
    } else {
      set(assets, allAssets);
    }
  } catch (e: any) {
    set(error, e.message);
  }
};

const pending: Record<string, AbortController> = {};

watch(search, search => {
  if (search) {
    set(loading, true);
  } else {
    set(loading, false);
  }
});

watchThrottled(
  search,
  async (search, old) => {
    if (!search) {
      return;
    }
    if (pending[old]) {
      pending[old].abort();
      delete pending[old];
    }
    set(error, '');
    set(loading, true);
    let controller = new AbortController();
    pending[search] = controller;
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
  if (get(includeNfts) && isNft(val)) {
    let details = get(getNftDetails(val));
    if (details) {
      set(assets, [
        ...get(assets),
        {
          ...details,
          identifier: value
        }
      ]);
    }
  } else {
    const mapping = await assetMapping([val]);
    set(assets, [
      ...get(assets),
      {
        identifier: value,
        ...mapping[val]
      }
    ]);
  }
};

onMounted(async () => {
  await checkValue();
});

watch(value, async () => {
  await checkValue();
});
</script>

<style scoped lang="scss">
:deep() {
  .v-select {
    &__slot {
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
    }

    &__selections {
      margin-top: 4px;
    }
  }
}

.asset-select {
  &__details {
    padding-top: 4px;
    padding-bottom: 4px;
  }

  &__loading {
    margin-top: -2px;
  }

  &--outlined {
    :deep() {
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
}
</style>
