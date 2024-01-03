import { type LiquityBalance } from '@rotki/common/lib/liquity';
import { type DefiProtocol } from '@/types/modules';

export interface LiquityLoan {
  readonly owner: string;
  readonly protocol: DefiProtocol;
  readonly balance: LiquityBalance;
}
