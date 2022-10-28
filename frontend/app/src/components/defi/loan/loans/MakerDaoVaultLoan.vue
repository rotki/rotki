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
      <v-row class="mt-8" no-gutters>
        <v-col cols="12">
          <premium-card
            v-if="!premium"
            :title="tc('maker_dao_vault_loan.borrowing_history')"
          />
          <vault-events-list
            v-else
            :asset="vault.collateral.asset"
            :events="events"
            :creation="creation"
            @open-link="openLink($event)"
          />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
import MakerDaoVaultCollateral from '@/components/defi/loan/loans/makerdao/MakerDaoVaultCollateral.vue';
import MakerDaoVaultDebtDetails from '@/components/defi/loan/loans/makerdao/MakerDaoVaultDebtDetails.vue';
import MakerDaoVaultLiquidation from '@/components/defi/loan/loans/makerdao/MakerDaoVaultLiquidation.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import { useInterop } from '@/electron-interop';
import { VaultEventsList } from '@/premium/premium';
import { usePremiumStore } from '@/store/session/premium';
import { useSessionSettingsStore } from '@/store/settings/session';
import {
  MakerDAOVault,
  MakerDAOVaultDetails,
  MakerDAOVaultEvent,
  MakerDAOVaultModel
} from '@/types/defi/maker';
import { Zero } from '@/utils/bignumbers';

const props = defineProps({
  vault: {
    required: true,
    type: Object as PropType<MakerDAOVaultModel>
  }
});

const { vault } = toRefs(props);
const { scrambleData } = storeToRefs(useSessionSettingsStore());
const { premium } = storeToRefs(usePremiumStore());
const { openUrl } = useInterop();
const { tc } = useI18n();

const openLink = (url: string) => {
  openUrl(url);
};

const totalInterestOwed = computed(() => {
  const makerVault = get(vault);
  if ('totalInterestOwed' in makerVault) {
    return (get(vault) as MakerDAOVault & MakerDAOVaultDetails)
      .totalInterestOwed;
  }
  return Zero;
});

const events = computed<MakerDAOVaultEvent[] | undefined>(() => {
  const makerVault = get(vault);
  if ('totalInterestOwed' in makerVault) {
    return makerVault.events;
  }
  return undefined;
});

const creation = computed(() => {
  const makerVault = get(vault);
  if ('totalInterestOwed' in makerVault) {
    return makerVault.creationTs;
  }
  return undefined;
});

const header = computed(() => {
  const makerVault = get(vault);
  return {
    identifier: scrambleData ? '-' : makerVault.identifier,
    collateralType: makerVault.collateralType
  };
});
</script>
