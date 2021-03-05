<template>
  <span
    v-bind="$attrs"
    class="asset-details-base pt-3 pb-3"
    :class="opensDetails ? 'asset-details-base--link' : null"
    @click="navigate"
  >
    <crypto-icon
      size="26px"
      class="asset-details-base__icon"
      :symbol="asset.symbol"
    />
    <span class="asset-details-base__details">
      <span
        class="asset-details-base__details__symbol"
        data-cy="details-symbol"
      >
        {{ symbol }}
      </span>
      <span class="grey--text asset-details-base__details__subtitle">
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
import CryptoIcon from '@/components/CryptoIcon.vue';
import { Routes } from '@/router/routes';

type Asset = {
  readonly symbol: string;
  readonly name: string;
};

@Component({
  components: { CryptoIcon }
})
export default class AssetDetailsBase extends Vue {
  @Prop({ required: true })
  asset!: Asset;

  @Prop({ required: false, type: Boolean, default: false })
  opensDetails!: boolean;

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
      path: Routes.ASSETS.replace(':identifier', this.asset.symbol)
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

    &__subtitle {
      font-size: 0.8rem;
    }
  }
}
</style>
