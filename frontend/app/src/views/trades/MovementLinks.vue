<template>
  <span class="d-flex flex-column pt-1">
    <span v-if="item.address" class="d-flex flex-row">
      <span class="mr-1 font-weight-medium">
        {{ $t('movement_links.address') }}
      </span>
      <hash-link :text="item.address" :base-url="addressBaseUrl" full-address />
    </span>
    <span v-if="item.transactionId" class="d-flex flex-row mt-1">
      <span class="mr-1 font-weight-medium">
        {{ $t('movement_links.transaction') }}
      </span>
      <hash-link
        :text="item.transactionId"
        :base-url="transactionBaseUrl"
        full-address
      />
    </span>
  </span>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import HashLink from '@/components/helper/HashLink.vue';
import { AssetMovement } from '@/services/balances/types';

@Component({
  components: { HashLink },
  computed: { ...mapGetters('balances', ['isEthereumToken']) }
})
export default class MovementLinks extends Vue {
  private etherscanAddress = 'https://etherscan.io/address/';
  private etherscanTransaction = 'https://etherscan.io/tx/';
  private blockstreamInfoAddress = 'https://blockstream.info/address/';
  private blockstreamInfoTransaction = 'https://blockstream.info/tx/';

  isEthereumToken!: (asset: string) => boolean;

  @Prop({ required: true })
  item!: AssetMovement;

  get isBtc(): boolean {
    return this.item.asset === 'BTC';
  }

  get isEthOrToken(): boolean {
    return this.item.asset === 'ETH' || this.isEthereumToken(this.item.asset);
  }

  get addressBaseUrl(): string | null {
    if (this.isBtc) {
      return this.blockstreamInfoAddress;
    } else if (this.isEthOrToken) {
      return this.etherscanAddress;
    }
    return null;
  }

  get transactionBaseUrl(): string | null {
    if (this.isBtc) {
      return this.blockstreamInfoTransaction;
    } else if (this.isEthOrToken) {
      return this.etherscanTransaction;
    }
    return null;
  }
}
</script>
