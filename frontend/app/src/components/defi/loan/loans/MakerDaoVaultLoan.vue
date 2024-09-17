<script setup lang="ts">
import { type BigNumber, Blockchain, HistoryEventEntryType } from '@rotki/common';
import type { MakerDAOVaultModel } from '@/types/defi/maker';

const props = defineProps<{
  vault: MakerDAOVaultModel;
}>();

const premium = usePremium();
const { t } = useI18n();

const totalInterestOwed = computed<BigNumber>(() => {
  const makerVault = props.vault;
  if ('totalInterestOwed' in makerVault)
    return makerVault.totalInterestOwed;

  return Zero;
});

const owner = computed(() => props.vault.owner || '');

const { scrambleIdentifier } = useScramble();

const header = computed(() => {
  const makerVault = props.vault;
  return {
    identifier: scrambleIdentifier(makerVault.identifier),
    collateralType: makerVault.collateralType,
  };
});

const chain = Blockchain.ETH;
</script>

<template>
  <div class="flex flex-col gap-4">
    <LoanHeader
      v-if="vault.owner"
      :owner="vault.owner"
    >
      {{ t('maker_dao_vault_loan.header', header) }}
    </LoanHeader>

    <div class="grid md:grid-cols-2 gap-4">
      <MakerDaoVaultCollateral :vault="vault" />
      <MakerDaoVaultLiquidation :vault="vault" />
    </div>

    <LoanDebt
      :debt="vault.debt"
      :asset="vault.collateral.asset"
    >
      <MakerDaoVaultDebtDetails
        :total-interest-owed="totalInterestOwed"
        :loading="!totalInterestOwed"
        :stability-fee="vault.stabilityFee"
      />
    </LoanDebt>

    <PremiumCard
      v-if="!premium"
      :title="t('maker_dao_vault_loan.borrowing_history')"
    />
    <HistoryEventsView
      v-else
      use-external-account-filter
      :section-title="t('common.events')"
      :protocols="['makerdao', 'makerdao vault']"
      :external-account-filter="[{ chain, address: owner }]"
      :only-chains="[chain]"
      :entry-types="[HistoryEventEntryType.EVM_EVENT]"
    />
  </div>
</template>
