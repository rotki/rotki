<template>
  <v-row>
    <v-col class="loan-header">
      <div v-if="isVault" class="loan-header__identifier">
        {{
          $t('loan_header.maker_vault', {
            identifier: scrambleData ? '-' : getSymbol(loan.identifier),
            collateralType: loan.collateralType
          })
        }}
      </div>
      <div v-if="isAave" class="loan-header__identifier">
        {{ $t('loan_header.aave_loan', { asset: getSymbol(loan.asset) }) }}
      </div>
      <div v-if="isCompound" class="loan-header__identifier">
        {{ $t('loan_header.compound_loan', { asset: getSymbol(loan.asset) }) }}
      </div>
      <div class="loan-header__owner secondary--text text--lighten-2">
        {{ $t('loan_header.owned_by') }}
        <hash-link :text="loan.owner" class="d-inline font-weight-medium" />
      </div>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import LoanDisplayMixin from '@/components/defi/loan/loan-display-mixin';
import HashLink from '@/components/helper/HashLink.vue';
import AssetMixin from '@/mixins/asset-mixin';
import ScrambleMixin from '@/mixins/scramble-mixin';

@Component({
  components: { HashLink }
})
export default class LoanHeader extends Mixins(
  LoanDisplayMixin,
  ScrambleMixin,
  AssetMixin
) {}
</script>

<style lang="scss" scoped>
.loan-header {
  &__identifier {
    font-size: 24px;
    font-weight: bold;
  }
}
</style>
