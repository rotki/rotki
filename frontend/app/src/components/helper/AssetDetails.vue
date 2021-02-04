<template>
  <span class="asset-details pt-3 pb-3" @click="navigate">
    <crypto-icon size="26px" class="asset-details__icon" :symbol="asset" />
    <span class="asset-details__details">
      <span class="asset-details__details__symbol">
        {{ symbol }}
      </span>
      <span class="grey--text asset-details__details__subtitle">
        <v-tooltip open-delay="400" top :disabled="$vuetify.breakpoint.lgAndUp">
          <template #activator="{ on, attrs }">
            <span v-bind="attrs" v-on="on">{{ name }}</span>
          </template>
          <span> {{ fullName }}</span>
        </v-tooltip>
      </span>
    </span>
  </span>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import { Routes } from '@/router/routes';
import { SupportedAsset } from '@/services/types-model';

@Component({
  components: { CryptoIcon },
  computed: {
    ...mapGetters('balances', ['assetInfo'])
  }
})
export default class AssetDetails extends Vue {
  @Prop({
    required: true,
    validator(value: string): boolean {
      return !!value && value.length > 0;
    }
  })
  asset!: string;
  assetInfo!: (key: string) => SupportedAsset;

  get symbol(): string {
    const details = this.details;
    return details ? details.symbol : this.asset;
  }

  get fullName(): string {
    const details = this.details;
    return details ? details.name : this.asset;
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

  get details(): SupportedAsset {
    return this.assetInfo(this.asset);
  }

  navigate() {
    this.$router.push({
      path: Routes.ASSETS.replace(':identifier', this.asset)
    });
  }
}
</script>

<style scoped lang="scss">
.asset-details {
  display: flex;
  flex-direction: row;
  align-items: center;
  cursor: pointer;

  &__icon {
    margin-right: 8px;
  }

  &__details {
    display: flex;
    flex-direction: column;

    &__subtitle {
      font-size: 0.8rem;
      white-space: nowrap;
    }
  }
}
</style>
