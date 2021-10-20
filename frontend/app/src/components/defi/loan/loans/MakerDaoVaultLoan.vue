<template>
  <v-row>
    <v-col cols="12">
      <loan-header class="mt-8 mb-6" :owner="vault.owner">
        {{
          $t('maker_dao_vault_loan.header', {
            identifier: scrambleData ? '-' : vault.identifier,
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
          <loan-debt :debt="vault.debt" :asset="vault.collateralAsset">
            <maker-dao-vault-debt-details
              :total-interest-owed="totalInterestOwed"
              :loading="!vault.totalInterestOwed"
              :stability-fee="vault.stabilityFee"
            />
          </loan-debt>
        </v-col>
      </v-row>
      <v-row class="mt-8" no-gutters>
        <v-col cols="12">
          <premium-card
            v-if="!premium"
            :title="$t('maker_dao_vault_loan.borrowing_history')"
          />
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
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
import MakerDaoVaultCollateral from '@/components/defi/loan/loans/makerdao/MakerDaoVaultCollateral.vue';
import MakerDaoVaultDebtDetails from '@/components/defi/loan/loans/makerdao/MakerDaoVaultDebtDetails.vue';
import MakerDaoVaultLiquidation from '@/components/defi/loan/loans/makerdao/MakerDaoVaultLiquidation.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import { getPremium } from '@/composables/session';
import { interop } from '@/electron-interop';
import AssetMixin from '@/mixins/asset-mixin';
import ScrambleMixin from '@/mixins/scramble-mixin';
import { VaultEventsList } from '@/premium/premium';
import { MakerDAOVaultModel } from '@/store/defi/types';
import { Zero } from '@/utils/bignumbers';

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
  setup(props) {
    const { vault } = toRefs(props);
    const premium = getPremium();

    const openLink = (url: string) => {
      interop.openUrl(url);
    };

    const totalInterestOwed = computed(() => {
      if ('totalInterestOwed' in vault.value) {
        return vault.value.totalInterestOwed;
      }
      return Zero;
    });

    return {
      totalInterestOwed,
      premium,
      openLink
    };
  }
});
</script>
