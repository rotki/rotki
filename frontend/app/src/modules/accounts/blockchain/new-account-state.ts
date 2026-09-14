import type { AccountManageAdd, StakingValidatorManage } from '@/modules/accounts/blockchain/use-account-manage';
import { Blockchain } from '@rotki/common';
import { ALL_EVM_CHAINS } from '@/modules/accounts/accounts.activity';

export function createNewBlockchainAccount(): AccountManageAdd {
  return {
    chain: ALL_EVM_CHAINS,
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
