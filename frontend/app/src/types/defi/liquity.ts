import { type LiquityBalance } from '@rotki/common/lib/liquity';
import { type Module } from '@/types/modules';

export interface LiquityLoan {
  readonly owner: string;
  readonly protocol: Module;
  readonly balance: LiquityBalance;
}
