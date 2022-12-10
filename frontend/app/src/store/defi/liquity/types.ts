import { type DefiProtocol } from '@rotki/common/lib/blockchain';
import {
  type LiquityBalance,
  type TroveEvent
} from '@rotki/common/lib/liquity';

export interface LiquityLoan {
  readonly owner: string;
  readonly protocol: DefiProtocol;
  readonly balance: LiquityBalance;
  readonly events: TroveEvent[];
}
