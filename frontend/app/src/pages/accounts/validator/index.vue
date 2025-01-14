<script setup lang="ts">
import { useTemplateRef } from 'vue';
import { NoteLocation } from '@/types/notes';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useAccountImportProgressStore } from '@/store/use-account-import-progress-store';
import { useBlockchainAccountLoading } from '@/composables/accounts/blockchain/use-account-loading';
import AccountBalancesExportImport from '@/components/accounts/AccountBalancesExportImport.vue';
import AccountDialog from '@/components/accounts/management/AccountDialog.vue';
import AccountImportProgress from '@/components/accounts/AccountImportProgress.vue';
import EthStakingValidators from '@/components/accounts/EthStakingValidators.vue';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.ACCOUNTS_VALIDATOR,
  },
  name: 'accounts-validator',
});

const { t } = useI18n();

const account = ref<AccountManageState>();
const table = useTemplateRef<InstanceType<typeof EthStakingValidators>>('table');

const { importingAccounts } = storeToRefs(useAccountImportProgressStore());
const { isSectionLoading, refreshDisabled } = useBlockchainAccountLoading();

const router = useRouter();
const route = useRoute();

function createNewBlockchainAccount(): void {
  set(account, {
    chain: Blockchain.ETH2,
    data: {
      ownershipPercentage: '',
      publicKey: '',
      validatorIndex: '',
    },
    mode: 'add',
    type: 'validator',
  });
}

function refresh() {
  if (isDefined(table))
    get(table).refresh();
}

onMounted(async () => {
  const { query } = get(route);
  if (query.add) {
    createNewBlockchainAccount();
    await router.replace({ query: {} });
  }
});
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.accounts'),
      t('navigation_menu.accounts_sub.validator'),
    ]"
  >
    <template #buttons>
      <RuiButtonGroup
        variant="outlined"
        color="primary"
      >
        <RuiButton
          :disabled="refreshDisabled"
          :loading="isSectionLoading"
          @click="refresh()"
        >
          <template #prepend>
            <RuiIcon name="lu-refresh-ccw" />
          </template>
          {{ t('common.refresh') }}
        </RuiButton>
      </RuiButtonGroup>

      <RuiButton
        data-cy="add-blockchain-account"
        color="primary"
        @click="createNewBlockchainAccount()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('blockchain_balances.add_account') }}
      </RuiButton>

      <AccountBalancesExportImport />
    </template>
    <div>
      <AccountImportProgress
        v-if="importingAccounts"
        class="-mb-4 -mt-1"
      />

      <EthStakingValidators
        ref="table"
        @edit="account = $event"
      />

      <AccountDialog
        v-model="account"
        :chain-ids="[Blockchain.ETH2]"
        @complete="refresh()"
      />
    </div>
  </TablePageLayout>
</template>
