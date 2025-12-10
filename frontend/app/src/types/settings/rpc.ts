import type { Blockchain } from '@rotki/common';
import { z } from 'zod/v4';

const BlockchainRpcNode = z.object({
  active: z.boolean(),
  blockchain: z.string().min(1),
  endpoint: z.string(),
  identifier: z.number(),
  name: z.string().min(1),
  owned: z.boolean(),
  weight: z.preprocess(weight => Number.parseFloat(weight as string), z.number().nonnegative().max(100)),
});

export type BlockchainRpcNode = z.infer<typeof BlockchainRpcNode>;

export const BlockchainRpcNodeList = z.array(BlockchainRpcNode);

export type BlockchainRpcNodeList = z.infer<typeof BlockchainRpcNodeList>;

export function getPlaceholderNode(chain: Blockchain): BlockchainRpcNode {
  return {
    active: true,
    blockchain: chain,
    endpoint: '',
    identifier: -1,
    name: '',
    owned: true,
    weight: 0,
  };
}

interface EvmRpcNodeAddState {
  mode: 'add';
  node: BlockchainRpcNode;
}

interface EvmRpcNodeEditState {
  mode: 'edit';
  node: BlockchainRpcNode;
}

export type BlockchainRpcNodeManageState = EvmRpcNodeAddState | EvmRpcNodeEditState;
