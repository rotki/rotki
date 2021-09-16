<template>
  <v-row>
    <v-col cols="12">
      <loan-header class="mt-8 mb-6" :owner="vault.owner">
        {{
          $t('loan_header.maker_vault', {
            identifier: scrambleData ? '-' : getSymbol(vault.identifier),
            collateralType: vault.collateralType
          })
        }}
      </loan-header>
      <v-row no-gutters>
        <v-col cols="12" md="6" class="pe-md-4">
          <maker-dao-vault-collateral :vault="vault" />
        </v-col>
        <v-col cols="12" md="6" class="ps-md-4 pt-8 pt-md-0">
          <maker-dao-vault-liquidation :vault="vault" />
        </v-col>
        <v-col cols="12" class="pt-8 pt-md-8">
          <loan-debt :debt="vault.debt" :asset="vault.asset">
            <maker-dao-vault-debt-details
              :total-interest-owed="vault.totalInterestOwed"
              :stability-fee="vault.stabilityFee"
            />
          </loan-debt>
        </v-col>
      </v-row>
      <v-row class="mt-8" no-gutters>
        <v-col cols="12">
          <premium-card v-if="!premium" title="Borrowing History" />
          <vault-events-list
            v-else
            :asset="vault.collateral.asset"
            :events="vault.events"
            :creation="vault.creationTs"
            @open-link="openLink($event)"
          />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { computed, defineComponent, PropType } from '@vue/composition-api';
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
import MakerDaoVaultCollateral from '@/components/defi/loan/loans/makerdao/MakerDaoVaultCollateral.vue';
import MakerDaoVaultDebtDetails from '@/components/defi/loan/loans/makerdao/MakerDaoVaultDebtDetails.vue';
import MakerDaoVaultLiquidation from '@/components/defi/loan/loans/makerdao/MakerDaoVaultLiquidation.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import { interop } from '@/electron-interop';
import AssetMixin from '@/mixins/asset-mixin';
import ScrambleMixin from '@/mixins/scramble-mixin';
import { VaultEventsList } from '@/premium/premium';
import { MakerDAOVaultModel } from '@/store/defi/types';
import { useStore } from '@/store/utils';

export default defineComponent({
  name: 'MakerDaoVaultLoan',
  components: {
    MakerDaoVaultLiquidation,
    MakerDaoVaultCollateral,
    MakerDaoVaultDebtDetails,
    PremiumCard,
    LoanDebt,
    LoanHeader,
    VaultEventsList
  },
  mixins: [ScrambleMixin, AssetMixin],
  props: {
    vault: {
      required: true,
      type: Object as PropType<MakerDAOVaultModel>
    }
  },
  setup() {
    const store = useStore();
    const premium = computed(() => store.state.session!!.premium);

    const openLink = (url: string) => {
      interop.openUrl(url);
    };

    return {
      premium,
      openLink
    };
  }
});
</script>
