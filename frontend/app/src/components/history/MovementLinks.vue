<template>
  <span class="d-flex flex-column pt-1">
    <span v-if="item.address" class="d-flex flex-row">
      <span class="mr-1 font-weight-medium">
        {{ $t('movement_links.address') }}
      </span>
      <hash-link :text="item.address" :chain="chain" full-address />
    </span>
    <span v-if="item.transactionId" class="d-flex flex-row mt-1">
      <span class="mr-1 font-weight-medium">
        {{ $t('movement_links.transaction') }}
      </span>
      <hash-link :text="transactionId" :chain="chain" tx full-address />
    </span>
  </span>
</template>
<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import HashLink from '@/components/helper/HashLink.vue';
import { AssetMovement } from '@/services/history/types';

@Component({
  components: { HashLink },
  computed: { ...mapGetters('balances', ['isEthereumToken']) }
})
export default class MovementLinks extends Vue {
  isEthereumToken!: (asset: string) => boolean;

  @Prop({ required: true })
  item!: AssetMovement;

  get transactionId(): string {
    const { transactionId } = this.item;
    if (!transactionId) return '';

    if (this.chain !== Blockchain.ETH) {
      return transactionId;
    }
    return transactionId.startsWith('0x')
      ? transactionId
      : `0x${transactionId}`;
  }

  get chain(): string {
    if (
      this.isEthereumToken(this.item.asset) ||
      this.item.asset === Blockchain.ETH
    ) {
      return Blockchain.ETH;
    }
    return this.item.asset;
  }
}
</script>
