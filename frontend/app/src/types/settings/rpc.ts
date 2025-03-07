import type { Blockchain } from '@rotki/common';
import { z } from 'zod';

const EvmRpcNode = z.object({
  active: z.boolean(),
  blockchain: z.string().min(1),
  endpoint: z.string(),
  identifier: z.number(),
  name: z.string().min(1),
  owned: z.boolean(),
  weight: z.preprocess(weight => Number.parseFloat(weight as string), z.number().nonnegative().max(100)),
});

export type EvmRpcNode = z.infer<typeof EvmRpcNode>;

export const EvmRpcNodeList = z.array(EvmRpcNode);

export type EvmRpcNodeList = z.infer<typeof EvmRpcNodeList>;

export function getPlaceholderNode(chain: Blockchain): EvmRpcNode {
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

export interface EvmRpcNodeAddState {
  mode: 'add';
  node: EvmRpcNode;
}

export interface EvmRpcNodeEditState {
  mode: 'edit';
  node: EvmRpcNode;
}

export type EvmRpcNodeManageState = EvmRpcNodeAddState | EvmRpcNodeEditState;
