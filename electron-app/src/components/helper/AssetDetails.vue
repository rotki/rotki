<template>
  <span class="asset-details">
    <crypto-icon
      width="26px"
      class="asset-details__icon"
      :symbol="details.symbol"
    ></crypto-icon>
    <span class="asset-details__details">
      <span class="asset-details__details__symbol">
        {{ details.symbol }}
      </span>
      <span class="grey--text asset-details__details__subtitle">
        {{ details.name }}
      </span>
    </span>
  </span>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import { SupportedAsset } from '@/services/types-model';

const { mapGetters } = createNamespacedHelpers('balances');

@Component({
  components: { CryptoIcon },
  computed: {
    ...mapGetters(['assetInfo'])
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

  get details(): SupportedAsset {
    return this.assetInfo(this.asset);
  }
}
</script>

<style scoped lang="scss">
.asset-details {
  display: flex;
  flex-direction: row;
  align-items: center;

  &__icon {
    margin-right: 8px;
  }

  &__details {
    display: flex;
    flex-direction: column;

    &__subtitle {
      font-size: 0.8rem;
    }
  }
}
</style>
