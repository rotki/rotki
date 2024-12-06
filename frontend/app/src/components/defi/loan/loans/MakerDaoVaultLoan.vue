<script setup lang="ts">
import { type BigNumber, Blockchain, HistoryEventEntryType } from '@rotki/common';
import { useScramble } from '@/composables/scramble';
import { usePremium } from '@/composables/premium';
import HistoryEventsView from '@/components/history/events/HistoryEventsView.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import MakerDaoVaultDebtDetails from '@/components/defi/loan/loans/makerdao/MakerDaoVaultDebtDetails.vue';
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import MakerDaoVaultLiquidation from '@/components/defi/loan/loans/makerdao/MakerDaoVaultLiquidation.vue';
import MakerDaoVaultCollateral from '@/components/defi/loan/loans/makerdao/MakerDaoVaultCollateral.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
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
    collateralType: makerVault.collateralType,
    identifier: scrambleIdentifier(makerVault.identifier),
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
