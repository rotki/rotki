<template>
  <blockchain-account-selector
    :value="addresses"
    flat
    label="Select address(es)"
    multiple
    :loading="loading"
    @input="added($event)"
  />
</template>

<script lang="ts">
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import {
  QueriedAddresses,
  QueriedAddressPayload,
  SupportedModules
} from '@/services/session/types';

@Component({
  components: { BlockchainAccountSelector },
  methods: {
    ...mapState('session', ['queriedAddresses']),
    ...mapActions('session', ['deleteQueriedAddress', 'addQueriedAddress'])
  }
})
export default class DefiQueriableAddress extends Vue {
  @Prop({ required: true })
  module!: SupportedModules;
  loading: boolean = false;
  addresses: string[] = [];
  addQueriedAddress!: (payload: QueriedAddressPayload) => Promise<void>;
  deleteQueriedAddress!: (payload: QueriedAddressPayload) => Promise<void>;

  queriedAddresses!: QueriedAddresses;

  async created() {
    await this.onAddressesChange();
  }

  @Watch('queriedAddresses')
  onAddressesChange() {
    const addresses = this.queriedAddresses[this.module];
    if (addresses) {
      this.addresses = addresses;
    }
  }

  async added(addresses: string[]) {
    this.loading = true;
    const added = addresses.filter(
      address => !this.addresses.includes(address)
    );
    const removed = this.addresses.filter(
      address => !addresses.includes(address)
    );

    if (added.length > 0) {
      await this.addQueriedAddress({
        address: added[0],
        module: this.module
      });
    } else if (removed.length > 0) {
      await this.deleteQueriedAddress({
        address: removed[0],
        module: this.module
      });
    }

    this.addresses = addresses;
    this.loading = false;
  }
}
</script>

<style scoped></style>
