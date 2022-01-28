<template>
  <v-autocomplete
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
      <v-list-item-avatar>
        <asset-icon
          size="50px"
          :identifier="item.identifier"
          :symbol="item.symbol"
        />
      </v-list-item-avatar>
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
import AssetDetails from '@/components/helper/AssetDetails.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { setupSupportedAssets } from '@/composables/balances';
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
    persistentHint: { required: false, type: Boolean, default: false }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { items } = toRefs(props);
    const { supportedAssets } = setupSupportedAssets();

    const input = (_value: string) => emit('input', _value);

    const search = ref<string>('');
    const visibleAssets = ref<SupportedAsset[]>([]);

    const keyword = computed<string>(() => {
      if (!search.value) {
        return '';
      }

      return search.value.toLocaleLowerCase().trim();
    });

    const getAvailableAssets = () => {
      if (items.value && items.value.length > 0) {
        return supportedAssets.value.filter(asset =>
          items.value!.includes(asset.identifier)
        );
      }
      return supportedAssets.value;
    };

    const setDefaultVisibleAssets = () => {
      visibleAssets.value = getAvailableAssets();
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

      visibleAssets.value = assets
        .filter(value1 => customFilter(value1, search))
        .sort((a, b) => compareAssets(a, b, 'name', keyword.value, false));
    });

    const assetText = (asset: SupportedAsset): string => {
      return `${asset.symbol} ${asset.name}`;
    };

    const blur = () => {
      setTimeout(() => {
        search.value = '';
      }, 200);
    };

    return {
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
