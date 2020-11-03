<template>
  <div
    class="account-balances"
    :class="`${blockchain.toLocaleLowerCase()}-account-balances`"
  >
    <v-row align="center">
      <v-col cols="auto" class="account-balances__column" />
      <v-col>
        <div class="text-h6 text-center account-balances__title">
          {{ title }}
        </div>
      </v-col>
      <v-col cols="auto">
        <refresh-button
          class="account-balances__refresh"
          :loading="isLoading"
          :tooltip="$t('account_balances.refresh_tooltip', { blockchain })"
          @refresh="refresh"
        />
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="6" offset="6">
        <tag-filter v-model="visibleTags" />
      </v-col>
    </v-row>
    <account-balance-table
      :blockchain="blockchain"
      :balances="balances"
      :visible-tags="visibleTags"
      @delete-click="toDeleteAccount = $event"
      @edit-click="editAccount($event)"
      @delete-xpub="xpubToDelete = $event"
    />
    <confirm-dialog
      :display="confirm"
      :title="$t('account_balances.confirm_delete.title')"
      :message="
        $t('account_balances.confirm_delete.description', {
          address: pendingAddress
        })
      "
      @cancel="cancelDelete()"
      @confirm="deleteAccount()"
    />
  </div>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import AccountBalanceTable from '@/components/accounts/AccountBalanceTable.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import { TaskType } from '@/model/task-type';
import {
  BlockchainAccountWithBalance,
  AccountWithBalance,
  BlockchainBalancePayload,
  XpubPayload
} from '@/store/balances/types';
import { Blockchain } from '@/typing/types';

@Component({
  components: {
    AccountBalanceTable,
    RefreshButton,
    TagFilter,
    ConfirmDialog
  },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning'])
  }
})
export default class AccountBalances extends Vue {
  @Prop({ required: true })
  balances!: AccountWithBalance[];
  @Prop({ required: true })
  blockchain!: Blockchain;
  @Prop({ required: true })
  title!: string;

  visibleTags: string[] = [];
  editedAccount = '';
  toDeleteAccount: string = '';
  xpubToDelete: XpubPayload | null = null;

  isTaskRunning!: (type: TaskType) => boolean;

  get isLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  }

  get confirm(): boolean {
    return !!this.toDeleteAccount || !!this.xpubToDelete;
  }

  get pendingAddress(): string {
    if (this.xpubToDelete) {
      return this.xpubToDelete.xpub;
    }
    if (this.toDeleteAccount) {
      return this.toDeleteAccount;
    }

    return '';
  }

  @Emit()
  editAccount(account: BlockchainAccountWithBalance) {
    this.editedAccount = account.address;
    return account;
  }

  async deleteAccount() {
    if (this.toDeleteAccount) {
      const address = this.toDeleteAccount;
      const blockchain = this.blockchain;
      this.toDeleteAccount = '';

      await this.$store.dispatch('balances/removeAccount', {
        address,
        blockchain
      });
    } else if (this.xpubToDelete) {
      const payload = { ...this.xpubToDelete };
      this.xpubToDelete = null;
      await this.$store.dispatch('balances/deleteXpub', payload);
    }
  }

  cancelDelete() {
    this.toDeleteAccount = '';
    this.xpubToDelete = null;
  }

  refresh() {
    this.$store.dispatch('balances/fetchBlockchainBalances', {
      ignoreCache: true,
      blockchain: this.blockchain
    } as BlockchainBalancePayload);
  }
}
</script>

<style scoped lang="scss">
.account-balances {
  margin-top: 16px;
  margin-bottom: 16px;

  &__column {
    width: 80px;
  }
}
</style>
