<template>
  <v-row>
    <v-col class="loan-header">
      <div v-if="loan.protocol === 'makerdao'" class="loan-header__identifier">
        Maker Vault #{{ loan.identifier }} ({{ loan.collateralType }})
      </div>
      <div v-else class="loan-header__identifier">
        Aave Loan ({{ loan.asset }})
      </div>
      <div class="loan-header__owner secondary--text text--lighten-2">
        Owned by:
        <hash-link
          :text="loan.owner"
          class="d-inline font-weight-medium"
        ></hash-link>
      </div>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import LoanDisplayMixin from '@/components/defi/loan/loan-display-mixin';
import HashLink from '@/components/helper/HashLink.vue';

@Component({
  components: { HashLink }
})
export default class LoanHeader extends Mixins(LoanDisplayMixin) {}
</script>

<style lang="scss" scoped>
.loan-header {
  &__identifier {
    font-size: 24px;
    font-weight: bold;
  }
}
</style>
