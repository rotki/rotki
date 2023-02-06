import { type DefiProtocol } from '@rotki/common/lib/blockchain';
import { type LiquityBalance } from '@rotki/common/lib/liquity';

export interface LiquityLoan {
  readonly owner: string;
  readonly protocol: DefiProtocol;
  readonly balance: LiquityBalance;
}
