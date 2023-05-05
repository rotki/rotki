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
const { tc } = useI18n();

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
  <v-row>
    <v-col cols="12">
      <loan-header v-if="vault.owner" class="mt-8 mb-6" :owner="vault.owner">
        {{ tc('maker_dao_vault_loan.header', 0, header) }}
      </loan-header>
      <v-row no-gutters>
        <v-col cols="12" md="6" class="pe-md-4">
          <maker-dao-vault-collateral :vault="vault" />
        </v-col>
        <v-col cols="12" md="6" class="ps-md-4 pt-8 pt-md-0">
          <maker-dao-vault-liquidation :vault="vault" />
        </v-col>
        <v-col cols="12" class="pt-8 pt-md-8">
          <loan-debt :debt="vault.debt" :asset="vault.collateral.asset">
            <maker-dao-vault-debt-details
              :total-interest-owed="totalInterestOwed"
              :loading="!totalInterestOwed"
              :stability-fee="vault.stabilityFee"
            />
          </loan-debt>
        </v-col>
      </v-row>
      <v-row v-if="!premium" class="mt-8" no-gutters>
        <v-col cols="12">
          <premium-card
            v-if="!premium"
            :title="tc('maker_dao_vault_loan.borrowing_history')"
          />
        </v-col>
      </v-row>
      <div v-else>
        <history-events-view
          :section-title="tc('common.events')"
          :protocols="['makerdao', 'makerdao vault']"
          :use-external-account-filter="true"
          :external-account-filter="[{ chain, address: vault.owner }]"
          :only-chains="[chain]"
          :entry-types="[HistoryEventEntryType.EVM_EVENT]"
        />
      </div>
    </v-col>
  </v-row>
</template>
