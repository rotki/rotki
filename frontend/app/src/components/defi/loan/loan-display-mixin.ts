import { Component, Prop, Vue } from 'vue-property-decorator';
import { AaveLoan, CompoundLoan, MakerDAOVaultModel } from '@/store/defi/types';

@Component({})
export default class LoanDisplayMixin extends Vue {
  @Prop({ required: true })
  loan!: MakerDAOVaultModel | AaveLoan | CompoundLoan | null;

  get isVault(): boolean {
    return this.loan?.protocol === 'makerdao';
  }

  get isAave(): boolean {
    return this.loan?.protocol === 'aave';
  }

  get isCompound(): boolean {
    return this.loan?.protocol === 'compound';
  }
}
