<template>
  <span
    v-bind="$attrs"
    class="asset-details-base pt-3 pb-3"
    :class="opensDetails ? 'asset-details-base--link' : null"
    @click="navigate"
  >
    <asset-icon
      :changeable="changeable"
      size="26px"
      class="asset-details-base__icon"
      :identifier="identifier"
      :symbol="symbol"
    />
    <span class="asset-details-base__details ms-2">
      <span
        class="asset-details-base__details__symbol"
        data-cy="details-symbol"
      >
        {{ symbol }}
      </span>
      <span
        v-if="!hideName"
        class="grey--text asset-details-base__details__subtitle"
      >
        <v-tooltip open-delay="400" top :disabled="$vuetify.breakpoint.lgAndUp">
          <template #activator="{ on, attrs }">
            <span v-bind="attrs" class="text-truncate" v-on="on">
              {{ name }}
            </span>
          </template>
          <span> {{ fullName }}</span>
        </v-tooltip>
      </span>
    </span>
  </span>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { Routes } from '@/router/routes';
import { SupportedAsset } from '@/services/assets/types';

@Component({
  components: { AssetIcon }
})
export default class AssetDetailsBase extends Vue {
  @Prop({ required: true })
  asset!: SupportedAsset;
  @Prop({ required: false, type: Boolean, default: false })
  opensDetails!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  changeable!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  hideName!: boolean;

  get identifier(): string {
    if ('ethereumAddress' in this.asset) {
      return `_ceth_${this.asset.ethereumAddress}`;
    }
    return this.asset.identifier;
  }

  get symbol(): string {
    return this.asset.symbol;
  }

  get fullName(): string {
    return this.asset.name;
  }

  get name(): string {
    const name = this.fullName;
    const truncLength = 7;
    const xsOnly = this.$vuetify.breakpoint.mdAndDown;
    const length = name.length;

    if (!xsOnly || (length <= truncLength * 2 && xsOnly)) {
      return name;
    }

    return (
      name.slice(0, truncLength) +
      '...' +
      name.slice(length - truncLength, length)
    );
  }

  navigate() {
    if (!this.opensDetails) {
      return;
    }
    this.$router.push({
      path: Routes.ASSETS.replace(':identifier', this.identifier ?? this.symbol)
    });
  }
}
</script>

<style scoped lang="scss">
.asset-details-base {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;

  &--link {
    cursor: pointer;
  }

  &__icon {
    margin-right: 8px;
  }

  &__details {
    display: flex;
    flex-direction: column;
    width: 100%;

    &__symbol {
      text-overflow: ellipsis;
      overflow: hidden;
      white-space: nowrap;

      @media (min-width: 700px) and (max-width: 1500px) {
        width: 100px;
      }
    }

    &__subtitle {
      font-size: 0.8rem;
      text-overflow: ellipsis;
      overflow: hidden;
      white-space: nowrap;

      @media (min-width: 700px) and (max-width: 1500px) {
        width: 100px;
      }
    }

    @media (min-width: 700px) and (max-width: 1500px) {
      width: 100px;
    }
  }

  @media (min-width: 700px) and (max-width: 1500px) {
    width: 100px;
  }
}
</style>
