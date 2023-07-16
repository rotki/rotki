<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { type ComputedRef } from 'vue';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type MakerDAOVaultModel } from '@/types/defi/maker';

const props = defineProps<{
  vault: MakerDAOVaultModel;
}>();

const { vault } = toRefs(props);
const { premium } = storeToRefs(usePremiumStore());
const { t } = useI18n();

const totalInterestOwed: ComputedRef<BigNumber> = computed(() => {
  const makerVault = get(vault);
  if ('totalInterestOwed' in makerVault) {
    return makerVault.totalInterestOwed;
  }
  return Zero;
});

const { scrambleIdentifier } = useScramble();

const header = computed(() => {
  const makerVault = get(vault);
  return {
    identifier: scrambleIdentifier(makerVault.identifier),
    collateralType: makerVault.collateralType
  };
});

const chain = Blockchain.ETH;
</script>

<template>
  <VRow>
    <VCol cols="12">
      <LoanHeader v-if="vault.owner" class="mt-8 mb-6" :owner="vault.owner">
        {{ t('maker_dao_vault_loan.header', header) }}
      </LoanHeader>
      <VRow no-gutters>
        <VCol cols="12" md="6" class="pe-md-4">
          <MakerDaoVaultCollateral :vault="vault" />
        </VCol>
        <VCol cols="12" md="6" class="ps-md-4 pt-8 pt-md-0">
          <MakerDaoVaultLiquidation :vault="vault" />
        </VCol>
        <VCol cols="12" class="pt-8 pt-md-8">
          <LoanDebt :debt="vault.debt" :asset="vault.collateral.asset">
            <MakerDaoVaultDebtDetails
              :total-interest-owed="totalInterestOwed"
              :loading="!totalInterestOwed"
              :stability-fee="vault.stabilityFee"
            />
          </LoanDebt>
        </VCol>
      </VRow>
      <VRow v-if="!premium" class="mt-8" no-gutters>
        <VCol cols="12">
          <PremiumCard
            v-if="!premium"
            :title="t('maker_dao_vault_loan.borrowing_history')"
          />
        </VCol>
      </VRow>
      <div v-else>
        <HistoryEventsView
          :section-title="t('common.events')"
          :protocols="['makerdao', 'makerdao vault']"
          :use-external-account-filter="true"
          :external-account-filter="[{ chain, address: vault.owner }]"
          :only-chains="[chain]"
          :entry-types="[HistoryEventEntryType.EVM_EVENT]"
        />
      </div>
    </VCol>
  </VRow>
</template>
