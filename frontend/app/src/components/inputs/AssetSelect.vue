<template>
  <v-autocomplete
    :value="value"
    :disabled="disabled"
    :items="assets"
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
    :item-text="assetText"
    :menu-props="{ closeOnContentClick: true }"
    :outlined="outlined"
    :class="outlined ? 'asset-select--outlined' : null"
    @input="input"
  >
    <template #selection="{ item }">
      <asset-details class="asset-select__details" :asset="item.identifier" />
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
        <v-list-item-title>{{ item.symbol }}</v-list-item-title>
        <v-list-item-subtitle>{{ item.name }}</v-list-item-subtitle>
      </v-list-item-content>
    </template>
  </v-autocomplete>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { SupportedAsset } from '@/services/types-model';

const { mapState } = createNamespacedHelpers('balances');

@Component({
  components: { AssetDetails, AssetIcon },
  computed: {
    ...mapState(['supportedAssets'])
  }
})
export default class AssetSelect extends Vue {
  supportedAssets!: SupportedAsset[];

  @Prop({ required: false, default: null })
  items!: string[] | null;

  @Prop({ required: false, default: '' })
  hint!: string;

  @Prop({ required: false, default: '' })
  successMessages!: string;

  @Prop({ required: false, default: '' })
  errorMessages!: string;

  @Prop({ required: false, default: 'Asset' })
  label!: string;

  @Prop({ required: true, default: '' })
  value!: string;

  @Prop({ default: () => [], required: false })
  rules!: ((v: string) => boolean | string)[];

  @Prop({ default: false, required: false })
  disabled!: boolean;

  @Prop({ default: false, required: false, type: Boolean })
  outlined!: boolean;

  @Prop({ default: false, required: false, type: Boolean })
  clearable!: boolean;

  @Prop({ default: false, required: false, type: Boolean })
  persistentHint!: boolean;

  @Emit()
  input(_value: string) {}

  get assets(): SupportedAsset[] {
    if (this.items) {
      return this.supportedAssets.filter(asset =>
        this.items!.includes(asset.identifier)
      );
    }

    return this.supportedAssets;
  }

  assetText(asset: SupportedAsset): string {
    return `${asset.symbol} ${asset.name}`;
  }
}
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
