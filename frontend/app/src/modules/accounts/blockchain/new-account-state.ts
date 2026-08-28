import type { AccountManageAdd, StakingValidatorManage } from '@/modules/accounts/blockchain/use-account-manage';
import { Blockchain } from '@rotki/common';

export function createNewBlockchainAccount(): AccountManageAdd {
  return {
    chain: 'all',
    data: [
      {
        address: '',
        tags: null,
      },
    ],
    mode: 'add',
    type: 'account',
  };
}

export function createNewAccountForChain(chain: string): AccountManageAdd | StakingValidatorManage {
  if (chain === Blockchain.ETH2) {
    return {
      chain: Blockchain.ETH2,
      data: {},
      mode: 'add',
      type: 'validator',
    };
  }

  return {
    ...createNewBlockchainAccount(),
    chain,
  };
}
