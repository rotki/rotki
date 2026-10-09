<script lang="ts" setup>
import { Blockchain } from '@rotki/common';
import AccountBalancesExportImport from '@/modules/accounts/AccountBalancesExportImport.vue';
import EvmAccountsRefreshMenu from '@/modules/accounts/EvmAccountsRefreshMenu.vue';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { ActivityPart } from '@/modules/task-center/core/types';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

const { addDisabled = false } = defineProps<{
  isAccountsTabSelected: boolean;
  addDisabled?: boolean;
}>();

const emit = defineEmits<{
  'refresh-click': [];
  'refresh': [];
  'add-account': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const menuOpen = ref<boolean>(false);

const { isSectionLoading, refreshDisabled } = useBlockchainAccountLoading('evm');
const { useIsActive, useIsActivePrefix } = useTaskCenter();
const eth2Querying = useIsActivePrefix(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.ETH2);
const eth2Hydrating = useBalanceRefreshState().useIsHydrating(Blockchain.ETH2);
const eth2Loading = logicOr(eth2Querying, eth2Hydrating);

const isEth2Loading = logicOr(
  eth2Loading,
  useIsActive(ActivityKind.STAKING, ActivityPart.VALIDATORS),
);
</script>

<template>
  <RuiButtonGroup
    v-if="isAccountsTabSelected"
    variant="outlined"
    color="primary"
  >
    <RuiButton
      :disabled="refreshDisabled"
      :loading="isSectionLoading"
      @click="emit('refresh-click')"
    >
      <template #prepend>
        <RuiIcon name="lu-refresh-ccw" />
      </template>
      {{ t('common.refresh') }}
    </RuiButton>
    <RuiMenu
      v-model="menuOpen"
      :options="{ placement: 'bottom-end' }"
      :class-names="{ root: 'flex' }"
    >
      <template #activator="{ attrs }">
        <RuiButton
          v-bind="{
            ...attrs,
            'data-testid': 'blockchain-account-refresh',
          }"
          color="primary"
          variant="outlined"
          class="outline-0! px-2"
        >
          <RuiIcon name="lu-chevron-down" />
        </RuiButton>
      </template>

      <!-- mounted per opening, so it always starts on its entries rather than a half-finished step -->
      <EvmAccountsRefreshMenu
        v-if="menuOpen"
        @close="menuOpen = false"
      />
    </RuiMenu>
  </RuiButtonGroup>

  <RuiButton
    v-else
    color="primary"
    variant="outlined"
    :loading="isEth2Loading"
    @click="emit('refresh')"
  >
    <template #prepend>
      <RuiIcon name="lu-refresh-ccw" />
    </template>
    {{ t('common.refresh') }}
  </RuiButton>

  <RuiTooltip
    :disabled="!addDisabled"
    :open-delay="300"
  >
    <template #activator>
      <RuiButton
        data-testid="add-blockchain-account"
        color="primary"
        :disabled="addDisabled"
        @click="emit('add-account')"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('blockchain_balances.add_account') }}
      </RuiButton>
    </template>
    {{ t('blockchain_balances.add_validator_premium') }}
  </RuiTooltip>

  <AccountBalancesExportImport />
</template>
