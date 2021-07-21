import { Component, Prop, Vue } from 'vue-property-decorator';
import { DefiProtocol } from '@/services/defi/consts';
import { CompoundLoan } from '@/services/defi/types/compound';
import { AaveLoan, MakerDAOVaultModel } from '@/store/defi/types';

@Component({})
export default class LoanDisplayMixin extends Vue {
  @Prop({ required: true })
  loan!: MakerDAOVaultModel | AaveLoan | CompoundLoan | null;

  get isVault(): boolean {
    return this.loan?.protocol === DefiProtocol.MAKERDAO_VAULTS;
  }

  get isAave(): boolean {
    return this.loan?.protocol === DefiProtocol.AAVE;
  }

  get isCompound(): boolean {
    return this.loan?.protocol === DefiProtocol.COMPOUND;
  }
}
