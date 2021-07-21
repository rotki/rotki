<template>
  <v-container>
    <price-refresh />
    <v-card class="blockchain-balances mt-8">
      <v-card-title>
        <card-title>
          {{ $t('blockchain_balances.title') }}
        </card-title>
      </v-card-title>
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
          :balances="blockchainAssets"
        />
      </v-card-text>
    </v-card>

    <account-balances
      v-if="ethAccounts.length > 0"
      class="mt-8"
      :title="$t('blockchain_balances.balances.eth')"
      blockchain="ETH"
      :balances="ethAccounts"
      @edit-account="edit($event)"
    />

    <account-balances
      v-if="btcAccounts.length > 0"
      class="mt-8"
      :title="$t('blockchain_balances.balances.btc')"
      blockchain="BTC"
      :balances="btcAccounts"
      @edit-account="edit($event)"
    />

    <account-balances
      v-if="kusamaBalances.length > 0"
      class="mt-8"
      :title="$t('blockchain_balances.balances.ksm')"
      blockchain="KSM"
      :balances="kusamaBalances"
      @edit-account="edit($event)"
    />

    <account-balances
      v-if="avaxAccounts.length > 0"
      class="mt-8"
      :title="$t('blockchain_balances.balances.avax')"
      blockchain="AVAX"
      :balances="avaxAccounts"
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
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import {
  AccountWithBalance,
  AssetBalance,
  BlockchainAccountWithBalance
} from '@/store/balances/types';

@Component({
  components: {
    CardTitle,
    PriceRefresh,
    AccountForm,
    AccountBalances,
    AssetBalances,
    BigDialog
  },
  computed: {
    ...mapGetters('balances', [
      'ethAccounts',
      'btcAccounts',
      'blockchainAssets',
      'kusamaBalances',
      'avaxAccounts'
    ])
  }
})
export default class BlockchainBalances extends Vue {
  ethAccounts!: AccountWithBalance[];
  btcAccounts!: BlockchainAccountWithBalance[];
  kusamaBalances!: AccountWithBalance[];
  avaxAccounts!: AccountWithBalance[];
  blockchainAssets!: AssetBalance[];

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

  mounted() {
    this.openDialog = !!this.$route.query.add;
  }
}
</script>
