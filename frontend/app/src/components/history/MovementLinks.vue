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
        :text="transactionId"
        :base-url="transactionBaseUrl"
        full-address
      />
    </span>
  </span>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import { explorerUrls } from '@/components/helper/asset-urls';
import HashLink from '@/components/helper/HashLink.vue';
import { AssetMovement } from '@/services/history/types';

@Component({
  components: { HashLink },
  computed: { ...mapGetters('balances', ['isEthereumToken']) }
})
export default class MovementLinks extends Vue {
  isEthereumToken!: (asset: string) => boolean;
  readonly urls = explorerUrls;

  @Prop({ required: true })
  item!: AssetMovement;

  get transactionId(): string {
    const { transactionId } = this.item;
    if (!this.isEthOrToken) {
      return transactionId;
    }
    return transactionId.startsWith('0x')
      ? transactionId
      : `0x${transactionId}`;
  }

  get isEtc(): boolean {
    return this.item.asset === 'ETC';
  }

  get isBtc(): boolean {
    return this.item.asset === 'BTC';
  }

  get isEthOrToken(): boolean {
    return this.item.asset === 'ETH' || this.isEthereumToken(this.item.asset);
  }

  get addressBaseUrl(): string | null {
    if (this.isBtc) {
      return this.urls.BTC.address;
    } else if (this.isEthOrToken) {
      return this.urls.ETH.address;
    } else if (this.isEtc) {
      return this.urls.ETC.address;
    }
    return null;
  }

  get transactionBaseUrl(): string | null {
    if (this.isBtc) {
      return this.urls.BTC.transaction;
    } else if (this.isEthOrToken) {
      return this.urls.ETH.transaction;
    } else if (this.isEtc) {
      return this.urls.ETC.transaction;
    }
    return null;
  }
}
</script>
