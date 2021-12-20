<template>
  <v-card
    class="account-balances"
    :class="`${blockchain.toLocaleLowerCase()}-account-balances`"
  >
    <v-card-title>
      <v-row align="center" no-gutters>
        <v-col cols="auto">
          <refresh-button
            class="account-balances__refresh"
            :loading="isLoading"
            :tooltip="$t('account_balances.refresh_tooltip', { blockchain })"
            @refresh="refresh"
          />
        </v-col>
        <v-col class="ps-2">
          <card-title>{{ title }}</card-title>
        </v-col>
      </v-row>
    </v-card-title>
    <v-card-text>
      <v-row align="center" class="mb-1">
        <v-col cols="12" sm="6">
          <v-tooltip top>
            <template #activator="{ on, attrs }">
              <span v-bind="attrs" v-on="on">
                <v-btn
                  data-cy="account-balances__delete-button"
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
        <v-col v-if="!isEth2" cols="12" sm="6">
          <tag-filter v-model="visibleTags" />
        </v-col>
      </v-row>
      <account-balance-table
        ref="balances"
        data-cy="blockchain-balances"
        :loopring="loopring"
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
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Ref } from '@vue/composition-api';
import { mapState } from 'pinia';
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import AccountBalanceTable from '@/components/accounts/AccountBalanceTable.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import {
  AccountWithBalance,
  BlockchainAccountWithBalance,
  BlockchainBalancePayload,
  XpubPayload
} from '@/store/balances/types';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

@Component({
  components: {
    CardTitle,
    AccountBalanceTable,
    RefreshButton,
    TagFilter,
    ConfirmDialog
  },
  computed: {
    ...mapState(useTasks, ['isTaskRunning'])
  },
  methods: {
    ...mapActions('balances', ['fetchLoopringBalances'])
  }
})
export default class AccountBalances extends Vue {
  @Prop({ required: true })
  balances!: AccountWithBalance[];
  @Prop({ required: true })
  blockchain!: Blockchain;
  @Prop({ required: true })
  title!: string;
  @Prop({ required: false, type: Boolean, default: false })
  loopring!: boolean;

  selectedAddresses: string[] = [];
  visibleTags: string[] = [];
  editedAccount = '';
  confirmDelete: boolean = false;
  xpubToDelete: XpubPayload | null = null;

  isTaskRunning!: (type: TaskType) => Ref<boolean>;
  fetchLoopringBalances!: (refresh: true) => Promise<void>;

  get isEth2() {
    return this.blockchain === Blockchain.ETH2;
  }

  get isLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES).value;
  }

  get operationRunning(): boolean {
    return (
      this.isTaskRunning(TaskType.ADD_ACCOUNT).value ||
      this.isTaskRunning(TaskType.REMOVE_ACCOUNT).value
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

      if (blockchain === Blockchain.ETH2) {
        await this.$store.dispatch(
          'balances/deleteEth2Validators',
          this.selectedAddresses
        );
      } else {
        await this.$store.dispatch('balances/removeAccount', {
          accounts: this.selectedAddresses,
          blockchain
        });
      }

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
    if (this.blockchain === Blockchain.ETH) {
      this.fetchLoopringBalances(true);
    }
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
