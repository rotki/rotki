import { Component, Prop, Vue } from 'vue-property-decorator';
import { AaveLoan, MakerDAOVaultModel } from '@/store/defi/types';

@Component({})
export default class LoanDisplayMixin extends Vue {
  @Prop({ required: true })
  loan!: MakerDAOVaultModel | AaveLoan | null;

  get isVault(): boolean {
    return this.loan?.protocol === 'makerdao';
  }
}
