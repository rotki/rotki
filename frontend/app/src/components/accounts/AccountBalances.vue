<template>
  <v-card :class="`${blockchain.toLocaleLowerCase()}-account-balances`">
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
      <v-row class="mb-2">
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
                  <span>{{ $tc('common.actions.delete') }}</span>
                </v-btn>
              </span>
            </template>
            <span>{{ $tc('account_balances.delete_tooltip') }}</span>
          </v-tooltip>
        </v-col>
        <v-col v-if="!isEth2" cols="12" sm="6">
          <tag-filter v-model="visibleTags" hide-details />
        </v-col>
      </v-row>
      <account-balance-table
        ref="balanceTable"
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
        :display="deleteConfirmed"
        :title="$tc('account_balances.confirm_delete.title')"
        :message="deleteDescription"
        @cancel="cancelDelete()"
        @confirm="deleteAccount()"
      />
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import AccountBalanceTable from '@/components/accounts/AccountBalanceTable.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import i18n from '@/i18n';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import {
  AccountWithBalance,
  BlockchainAccountWithBalance,
  XpubPayload
} from '@/store/balances/types';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

export default defineComponent({
  name: 'AccountBalances',
  components: {
    CardTitle,
    AccountBalanceTable,
    RefreshButton,
    TagFilter,
    ConfirmDialog
  },
  props: {
    balances: { required: true, type: Array as PropType<AccountWithBalance[]> },
    blockchain: { required: true, type: String as PropType<Blockchain> },
    title: { required: true, type: String },
    loopring: { required: false, type: Boolean, default: false }
  },
  emits: ['edit-account'],
  setup(props, { emit }) {
    const { blockchain } = toRefs(props);

    const { isTaskRunning } = useTasks();
    const { fetchLoopringBalances, fetchBlockchainBalances } =
      useBlockchainBalancesStore();

    const selectedAddresses = ref<string[]>([]);
    const visibleTags = ref<string[]>([]);
    const editedAccount = ref<string>('');
    const confirmDelete = ref<boolean>(false);
    const xpubToDelete = ref<XpubPayload | null>(null);
    const balanceTable = ref<any>(null);

    const isEth2 = computed<boolean>(() => {
      return get(blockchain) === Blockchain.ETH2;
    });
    const isQueryingBlockchain = isTaskRunning(
      TaskType.QUERY_BLOCKCHAIN_BALANCES
    );

    const isLoading = computed<boolean>(() => {
      if (!get(isEth2)) {
        return get(isQueryingBlockchain);
      }
      const isLoopringLoading = isTaskRunning(TaskType.L2_LOOPRING);

      return get(isQueryingBlockchain) || get(isLoopringLoading);
    });

    const operationRunning = computed<boolean>(() => {
      return (
        get(isTaskRunning(TaskType.ADD_ACCOUNT)) ||
        get(isTaskRunning(TaskType.REMOVE_ACCOUNT))
      );
    });

    const deleteConfirmed = computed<boolean>(() => {
      return get(confirmDelete) || !!get(xpubToDelete);
    });

    const deleteDescription = computed<string>(() => {
      if (get(xpubToDelete)) {
        return i18n.tc('account_balances.confirm_delete.description_xpub', 0, {
          address: get(xpubToDelete)!.xpub
        });
      }
      return i18n.tc('account_balances.confirm_delete.description_address', 0, {
        count: get(selectedAddresses).length
      });
    });

    const editAccount = (account: BlockchainAccountWithBalance) => {
      set(editedAccount, account.address);
      emit('edit-account', account);
    };

    const { deleteEth2Validators, removeAccount, deleteXpub } =
      useBlockchainAccountsStore();

    const deleteAccount = async () => {
      if (get(selectedAddresses).length > 0) {
        set(confirmDelete, false);

        if (get(isEth2)) {
          await deleteEth2Validators(get(selectedAddresses));
        } else {
          await removeAccount({
            accounts: get(selectedAddresses),
            blockchain: get(blockchain)
          });
        }

        set(selectedAddresses, []);
      } else if (get(xpubToDelete)) {
        const payload = { ...get(xpubToDelete)! };
        set(xpubToDelete, null);
        await deleteXpub(payload);
        get(balanceTable)?.removeCollapsed(payload);
      }
    };

    const cancelDelete = () => {
      set(confirmDelete, false);
      set(xpubToDelete, null);
    };

    const refresh = () => {
      fetchBlockchainBalances({
        ignoreCache: true,
        blockchain: get(blockchain)
      });
      if (get(blockchain) === Blockchain.ETH) {
        fetchLoopringBalances(true);
      }
    };

    return {
      balanceTable,
      isLoading,
      operationRunning,
      selectedAddresses,
      refresh,
      confirmDelete,
      isEth2,
      visibleTags,
      editAccount,
      xpubToDelete,
      deleteDescription,
      deleteConfirmed,
      cancelDelete,
      deleteAccount
    };
  }
});
</script>
