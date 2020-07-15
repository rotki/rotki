<template>
  <v-card class="blockchain-balances mt-8">
    <v-card-title>Blockchain Balances</v-card-title>
    <v-card-text>
      <v-btn absolute fab top right dark color="primary" @click="newAccount()">
        <v-icon>
          fa fa-plus
        </v-icon>
      </v-btn>
      <big-dialog
        :display="openDialog"
        :title="dialogTitle"
        :sub-title="dialogSubTitle"
        primary-action="Save"
        @confirm="save()"
        @cancel="clearDialog()"
      >
        <account-form ref="dialogChild" :edit="accountToEdit"></account-form>
      </big-dialog>
      <token-track></token-track>
      <v-divider></v-divider>
      <asset-balances title="Blockchain Balances per Asset" :balances="totals">
      </asset-balances>
      <v-divider></v-divider>
      <account-balances
        title="ETH per account balances"
        blockchain="ETH"
        :balances="ethAccounts"
        @editAccount="edit($event)"
      ></account-balances>
      <v-divider></v-divider>
      <account-balances
        title="BTC per account balances"
        blockchain="BTC"
        :balances="btcAccounts"
        @editAccount="edit($event)"
      ></account-balances>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import AccountForm from '@/components/accounts/AccountForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import TokenTrack from '@/components/settings/TokenTrack.vue';
import { AccountBalance } from '@/model/blockchain-balances';
import { Account } from '@/typing/types';

const { mapGetters } = createNamespacedHelpers('balances');

@Component({
  components: {
    AccountForm,
    AccountBalances,
    AssetBalances,
    BigDialog,
    TokenTrack
  },
  computed: {
    ...mapGetters(['ethAccounts', 'btcAccounts', 'totals'])
  }
})
export default class BlockchainBalances extends Vue {
  ethAccounts!: AccountBalance[];
  btcAccounts!: AccountBalance[];
  totals!: AccountBalance[];

  accountToEdit: Account | null = null;
  dialogTitle: string = '';
  dialogSubTitle: string = '';
  openDialog: boolean = false;

  newAccount() {
    this.accountToEdit = null;
    this.dialogTitle = 'Add Blockchain Account';
    this.dialogSubTitle = '';
    this.openDialog = true;
  }
  edit(account: Account) {
    this.accountToEdit = account;
    this.dialogTitle = 'Edit Blockchain Account';
    this.dialogSubTitle = 'Modify account details';
    this.openDialog = true;
  }

  async clearDialog() {
    interface dataForm extends Vue {
      editComplete(): void;
    }
    const form = this.$refs.dialogChild as dataForm;
    form.editComplete();
    this.openDialog = false;
  }

  async save() {
    interface dataForm extends Vue {
      addAccount(): Promise<boolean>;
    }
    const form = this.$refs.dialogChild as dataForm;
    form.addAccount().then(success => {
      if (success === true) this.clearDialog();
    });
  }
}
</script>
