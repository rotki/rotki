<template>
  <v-container>
    <v-card class="blockchain-balances mt-8">
      <v-card-title>{{ $t('blockchain_balances.title') }}</v-card-title>
      <v-card-text>
        <v-btn absolute fab top right color="primary" @click="newAccount()">
          <v-icon> mdi-plus </v-icon>
        </v-btn>
        <big-dialog
          :display="openDialog"
          :title="dialogTitle"
          :subtitle="dialogSubtitle"
          :primary-action="$t('blockchain_balances.form_dialog.save')"
          :secondary-action="$t('blockchain_balances.form_dialog.cancel')"
          :action-disabled="!valid"
          @confirm="save()"
          @cancel="clearDialog()"
        >
          <account-form ref="form" v-model="valid" :edit="accountToEdit" />
        </big-dialog>
        <asset-balances
          :title="$t('blockchain_balances.per_asset.title')"
          :balances="totals"
        />
      </v-card-text>
    </v-card>

    <account-balances
      class="mt-4"
      :title="$t('blockchain_balances.balances.eth')"
      blockchain="ETH"
      :balances="ethAccounts"
      @edit-account="edit($event)"
    />

    <account-balances
      class="mt-4"
      :title="$t('blockchain_balances.balances.btc')"
      blockchain="BTC"
      :balances="btcAccounts"
      @edit-account="edit($event)"
    />

    <account-balances
      class="mt-4"
      :title="$t('blockchain_balances.balances.ksm')"
      blockchain="KSM"
      :balances="kusamaBalances"
      @edit-account="edit($event)"
    />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import AccountForm from '@/components/accounts/AccountForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import {
  AccountWithBalance,
  BlockchainAccountWithBalance
} from '@/store/balances/types';

@Component({
  components: {
    AccountForm,
    AccountBalances,
    AssetBalances,
    BigDialog
  },
  computed: {
    ...mapGetters('balances', [
      'ethAccounts',
      'btcAccounts',
      'totals',
      'kusamaBalances'
    ])
  }
})
export default class BlockchainBalances extends Vue {
  ethAccounts!: AccountWithBalance[];
  btcAccounts!: BlockchainAccountWithBalance[];
  kusamaBalances!: AccountWithBalance[];
  totals!: AccountWithBalance[];

  accountToEdit: BlockchainAccountWithBalance | null = null;
  dialogTitle: string = '';
  dialogSubtitle: string = '';
  openDialog: boolean = false;
  valid: boolean = false;

  newAccount() {
    this.accountToEdit = null;
    this.dialogTitle = this.$tc('blockchain_balances.form_dialog.add_title');
    this.dialogSubtitle = '';
    this.openDialog = true;
  }

  edit(account: BlockchainAccountWithBalance) {
    this.accountToEdit = account;
    this.dialogTitle = this.$tc('blockchain_balances.form_dialog.edit_title');
    this.dialogSubtitle = this.$tc(
      'blockchain_balances.form_dialog.edit_subtitle'
    );
    this.openDialog = true;
  }

  async clearDialog() {
    this.openDialog = false;
    setTimeout(async () => {
      const form = this.$refs.form as AccountForm;
      if (form) {
        await form.reset();
      }
      this.accountToEdit = null;
    }, 300);
  }

  async save() {
    const form = this.$refs.form as AccountForm;
    const success = await form.save();
    if (success) {
      await this.clearDialog();
    }
  }
}
</script>
