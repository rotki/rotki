<template>
  <v-card
    class="account-balances"
    :class="`${blockchain.toLocaleLowerCase()}-account-balances`"
  >
    <v-card-title>
      <v-row align="center">
        <v-col>
          <div class="text-h6 account-balances__title">
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
    </v-card-title>
    <v-card-text>
      <v-row align="center">
        <v-col cols="6">
          <v-tooltip top>
            <template #activator="{ on, attrs }">
              <span v-bind="attrs" v-on="on">
                <v-btn
                  color="primary"
                  text
                  outlined
                  :disabled="
                    isLoading ||
                    operationRunning ||
                    selectedAddresses.length === 0
                  "
                  @click="confirmDelete = true"
                >
                  <v-icon> mdi-delete-outline </v-icon>
                  <span>{{ $t('account_balances.delete_button') }}</span>
                </v-btn>
              </span>
            </template>
            <span>{{ $t('account_balances.delete_tooltip') }}</span>
          </v-tooltip>
        </v-col>
        <v-col cols="6">
          <tag-filter v-model="visibleTags" />
        </v-col>
      </v-row>
      <account-balance-table
        ref="balances"
        :blockchain="blockchain"
        :balances="balances"
        :visible-tags="visibleTags"
        :selected="selectedAddresses"
        @edit-click="editAccount($event)"
        @delete-xpub="xpubToDelete = $event"
        @addresses-selected="selectedAddresses = $event"
      />
      <confirm-dialog
        :display="confirm"
        :title="$t('account_balances.confirm_delete.title')"
        :message="deleteDescription"
        @cancel="cancelDelete()"
        @confirm="deleteAccount()"
      />
    </v-card-text>
  </v-card>
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

  selectedAddresses: string[] = [];
  visibleTags: string[] = [];
  editedAccount = '';
  confirmDelete: boolean = false;
  xpubToDelete: XpubPayload | null = null;

  isTaskRunning!: (type: TaskType) => boolean;

  get isLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  }

  get operationRunning(): boolean {
    return (
      this.isTaskRunning(TaskType.ADD_ACCOUNT) ||
      this.isTaskRunning(TaskType.REMOVE_ACCOUNT)
    );
  }

  get confirm(): boolean {
    return this.confirmDelete || !!this.xpubToDelete;
  }

  get deleteDescription(): string {
    if (this.xpubToDelete) {
      return this.$tc('account_balances.confirm_delete.description_xpub', 0, {
        address: this.xpubToDelete.xpub
      });
    }
    return this.$tc('account_balances.confirm_delete.description_address', 0, {
      count: this.selectedAddresses.length
    });
  }

  @Emit()
  editAccount(account: BlockchainAccountWithBalance) {
    this.editedAccount = account.address;
    return account;
  }

  async deleteAccount() {
    if (this.selectedAddresses.length > 0) {
      const blockchain = this.blockchain;
      this.confirmDelete = false;

      await this.$store.dispatch('balances/removeAccount', {
        accounts: this.selectedAddresses,
        blockchain
      });
      this.selectedAddresses = [];
    } else if (this.xpubToDelete) {
      const payload = { ...this.xpubToDelete };
      this.xpubToDelete = null;
      await this.$store.dispatch('balances/deleteXpub', payload);
      (this.$refs.balances as AccountBalanceTable).removeCollapsed(payload);
    }
  }

  cancelDelete() {
    this.confirmDelete = false;
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
