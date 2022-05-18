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
    :error-messages="errorMessages"
    item-value="identifier"
    :filter="customFilter"
    :search-input.sync="search"
    :item-text="assetText"
    auto-select-first
    :menu-props="{ closeOnContentClick: true }"
    :outlined="outlined"
    :class="outlined ? 'asset-select--outlined' : null"
    @input="input"
    @blur="blur"
  >
    <template #selection="{ item }">
      <asset-details
        class="asset-select__details ml-2"
        :asset="item.identifier"
      />
    </template>
    <template #item="{ item }">
      <div class="pr-4">
        <asset-icon
          size="40px"
          :identifier="item.identifier"
          :symbol="item.symbol"
        />
      </div>
      <v-list-item-content :id="`asset-${item.identifier.toLocaleLowerCase()}`">
        <v-list-item-title class="font-weight-medium">
          {{ item.symbol }}
        </v-list-item-title>
        <v-list-item-subtitle>{{ item.name }}</v-list-item-subtitle>
      </v-list-item-content>
    </template>
  </v-autocomplete>
</template>

<script lang="ts">
import { SupportedAsset } from '@rotki/common/lib/data';
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set, useTimeoutFn } from '@vueuse/core';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useAssetInfoRetrieval, useIgnoredAssetsStore } from '@/store/assets';
import { compareAssets } from '@/utils/assets';

export default defineComponent({
  name: 'AssetSelect',
  components: { AssetDetails, AssetIcon },
  props: {
    items: {
      required: false,
      type: Array as PropType<string[]>,
      default: () => []
    },
    hint: { required: false, type: String, default: '' },
    successMessages: { required: false, type: String, default: '' },
    errorMessages: { required: false, type: String, default: '' },
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
    showIgnored: { required: false, type: Boolean, default: false }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { items, showIgnored } = toRefs(props);
    const assetInfoRetrievalStore = useAssetInfoRetrieval();
    const { isAssetIgnored } = useIgnoredAssetsStore();
    const { supportedAssets } = toRefs(assetInfoRetrievalStore);

    const input = (_value: string) => emit('input', _value);

    const autoCompleteInput = ref(null);

    const search = ref<string>('');
    const visibleAssets = ref<SupportedAsset[]>([]);

    const keyword = computed<string>(() => {
      if (!get(search)) {
        return '';
      }

      return get(search).toLocaleLowerCase().trim();
    });

    const getAvailableAssets = () => {
      const unIgnoredAssets = get(supportedAssets).filter(
        asset => get(showIgnored) || !get(isAssetIgnored(asset.identifier))
      );

      const itemsVal = get(items);
      if (itemsVal && itemsVal.length > 0) {
        return unIgnoredAssets.filter(asset =>
          itemsVal!.includes(asset.identifier)
        );
      }
      return unIgnoredAssets;
    };

    const setDefaultVisibleAssets = () => {
      set(visibleAssets, getAvailableAssets());
    };

    onMounted(() => {
      setDefaultVisibleAssets();
    });

    watch(items, () => {
      setDefaultVisibleAssets();
    });

    const customFilter = (item: SupportedAsset, queryText: string): boolean => {
      const toLower = (string?: string | null) => {
        return string?.toLocaleLowerCase()?.trim() ?? '';
      };
      const keyword = toLower(queryText);
      const name = toLower(item.name);
      const symbol = toLower(item.symbol);
      return name.indexOf(keyword) >= 0 || symbol.indexOf(keyword) >= 0;
    };

    watch(search, search => {
      const assets = getAvailableAssets();

      set(
        visibleAssets,
        assets
          .filter(value1 => customFilter(value1, search))
          .sort((a, b) => compareAssets(a, b, 'name', get(keyword), false))
      );
    });

    const assetText = (asset: SupportedAsset): string => {
      return `${asset.symbol} ${asset.name}`;
    };

    const blur = () => {
      useTimeoutFn(() => {
        set(search, '');
      }, 200);
    };

    return {
      autoCompleteInput,
      blur,
      visibleAssets,
      customFilter,
      search,
      assetText,
      input
    };
  }
});
</script>

<style scoped lang="scss">
::v-deep {
  .v-select {
    &__slot {
      height: 60px;

      .v-label {
        top: 20px;
      }

      .v-input {
        &__icon {
          padding-top: 20px;
        }
      }
    }
  }
}

.asset-select {
  &__details {
    padding-top: 4px;
    padding-bottom: 4px;
  }

  &--outlined {
    ::v-deep {
      .v-input {
        &__icon {
          &--append {
            i {
              bottom: 8px;
            }
          }

          &--clear {
            button {
              bottom: 8px;
            }
          }
        }
      }
    }
  }
}
</style>
