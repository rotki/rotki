<template>
  <blockchain-account-selector
    outlined
    :value="selectedAccounts"
    flat
    :label="$t('module_queried_address.label')"
    multiple
    :chains="['ETH']"
    :loading="loading"
    @input="added($event)"
  />
</template>

<script lang="ts">
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import {
  QueriedAddressPayload,
  SupportedModules
} from '@/services/session/types';
import { Account, GeneralAccount } from '@/typing/types';

@Component({
  components: { BlockchainAccountSelector },
  computed: {
    ...mapGetters('balances', ['accounts'])
  },
  methods: {
    ...mapActions('session', ['deleteQueriedAddress', 'addQueriedAddress'])
  }
})
export default class ModuleQueriedAddress extends Vue {
  @Prop({ required: true })
  module!: SupportedModules;
  @Prop({ required: true })
  selectedAddresses!: string[];

  loading: boolean = false;
  selectedAccounts: Account[] = [];
  addQueriedAddress!: (payload: QueriedAddressPayload) => Promise<void>;
  deleteQueriedAddress!: (payload: QueriedAddressPayload) => Promise<void>;
  accounts!: GeneralAccount[];

  async created() {
    this.onAddressesChange();
  }

  @Watch('selectedAddresses')
  onAddressesChange() {
    this.selectedAccounts = this.accounts.filter(account =>
      this.selectedAddresses.includes(account.address)
    );
  }

  async added(accounts: GeneralAccount[]) {
    this.loading = true;
    const addresses = accounts.map(({ address }) => address);
    const allAddresses = this.selectedAccounts.map(({ address }) => address);
    const added = addresses.filter(address => !allAddresses.includes(address));
    const removed = allAddresses.filter(
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

    this.selectedAccounts = this.accounts.filter(account =>
      addresses.includes(account.address)
    );
    this.loading = false;
  }
}
</script>
