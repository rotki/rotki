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
import { mapActions } from 'vuex';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import {
  QueriedAddressPayload,
  SupportedModules
} from '@/services/session/types';

@Component({
  components: { BlockchainAccountSelector },
  methods: {
    ...mapActions('session', ['deleteQueriedAddress', 'addQueriedAddress'])
  }
})
export default class DefiQueriableAddress extends Vue {
  @Prop({ required: true })
  module!: SupportedModules;
  @Prop({ required: true })
  selectedAddresses!: string[];

  loading: boolean = false;
  addresses: string[] = [];
  addQueriedAddress!: (payload: QueriedAddressPayload) => Promise<void>;
  deleteQueriedAddress!: (payload: QueriedAddressPayload) => Promise<void>;

  async created() {
    this.onAddressesChange();
  }

  @Watch('selectedAddresses')
  onAddressesChange() {
    this.addresses = this.selectedAddresses;
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
      for (const address of added) {
        await this.addQueriedAddress({
          address,
          module: this.module
        });
      }
    } else if (removed.length > 0) {
      for (const address of removed) {
        await this.deleteQueriedAddress({
          address,
          module: this.module
        });
      }
    }

    this.addresses = addresses;
    this.loading = false;
  }
}
</script>

<style scoped></style>
