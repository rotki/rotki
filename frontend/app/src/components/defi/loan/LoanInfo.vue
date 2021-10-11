<template>
  <maker-dao-vault-loan v-if="isVault" :vault="loan" />
  <aave-lending v-else-if="isAave" :loan="loan" />
  <compound-lending v-else-if="isCompound" :loan="loan" />
  <liquity-lending v-else-if="isLiquity" :loan="loan" />
</template>

<script lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import AaveLending from '@/components/defi/loan/loans/AaveLending.vue';
import CompoundLending from '@/components/defi/loan/loans/CompoundLending.vue';
import LiquityLending from '@/components/defi/loan/loans/LiquityLending.vue';
import MakerDaoVaultLoan from '@/components/defi/loan/loans/MakerDaoVaultLoan.vue';
import { CompoundLoan } from '@/services/defi/types/compound';
import { LiquityLoan } from '@/store/defi/liquity/types';
import { AaveLoan, MakerDAOVaultModel } from '@/store/defi/types';

type Loan = MakerDAOVaultModel | AaveLoan | CompoundLoan | LiquityLoan;

export default defineComponent({
  name: 'LoanInfo',
  components: {
    LiquityLending,
    CompoundLending,
    AaveLending,
    MakerDaoVaultLoan
  },
  props: {
    loan: {
      required: true,
      type: Object as PropType<Loan>
    }
  },
  setup(props) {
    const { loan } = toRefs(props);

    const create = (protocol: DefiProtocol) =>
      computed(() => loan.value?.protocol === protocol);
    const isVault = create(DefiProtocol.MAKERDAO_VAULTS);
    const isAave = create(DefiProtocol.AAVE);
    const isCompound = create(DefiProtocol.COMPOUND);
    const isLiquity = create(DefiProtocol.LIQUITY);

    return {
      isVault,
      isCompound,
      isAave,
      isLiquity
    };
  }
});
</script>
