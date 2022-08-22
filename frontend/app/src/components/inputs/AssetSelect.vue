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
    :hide-details="hideDetails"
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
        :enable-association="enableAssociation"
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
import { get, set, useTimeoutFn } from '@vueuse/core';
import { computed, defineComponent, PropType, ref, toRefs } from 'vue';
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
    excludes: {
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
    showIgnored: { required: false, type: Boolean, default: false },
    hideDetails: { required: false, type: Boolean, default: false },
    enableAssociation: { required: false, type: Boolean, default: true }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { items, showIgnored, enableAssociation, excludes } = toRefs(props);
    const assetInfoRetrievalStore = useAssetInfoRetrieval();
    const { isAssetIgnored } = useIgnoredAssetsStore();
    const { supportedAssets, allSupportedAssets } = toRefs(
      assetInfoRetrievalStore
    );

    const input = (_value: string) => emit('input', _value);

    const autoCompleteInput = ref(null);

    const search = ref<string>('');

    const keyword = computed<string>(() => {
      if (!get(search)) {
        return '';
      }

      return get(search).toLocaleLowerCase().trim();
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

    const visibleAssets = computed<SupportedAsset[]>(() => {
      const itemsVal = get(items);
      const excludesVal = get(excludes);

      let assets = (
        get(enableAssociation) ? get(supportedAssets) : get(allSupportedAssets)
      ).filter((asset: SupportedAsset) => {
        const unIgnored =
          get(showIgnored) || !get(isAssetIgnored(asset.identifier));

        const included =
          itemsVal && itemsVal.length > 0
            ? itemsVal.includes(asset.identifier)
            : true;

        const excluded =
          excludesVal && excludesVal.length > 0
            ? excludesVal.includes(asset.identifier)
            : false;

        return unIgnored && included && !excluded;
      });

      const searchVal = get(search);
      if (!searchVal) return assets;

      return assets
        .filter(item => customFilter(item, searchVal))
        .sort((a, b) => compareAssets(a, b, 'name', get(keyword), false));
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

  &--outlined {
    ::v-deep {
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
