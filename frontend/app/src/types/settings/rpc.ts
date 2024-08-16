import { z } from 'zod';
import type { Blockchain } from '@rotki/common';

const EvmRpcNode = z.object({
  identifier: z.number(),
  name: z.string().min(1),
  endpoint: z.string(),
  owned: z.boolean(),
  weight: z.preprocess(weight => Number.parseFloat(weight as string), z.number().nonnegative().max(100)),
  active: z.boolean(),
  blockchain: z.string().min(1),
});

export type EvmRpcNode = z.infer<typeof EvmRpcNode>;

export const EvmRpcNodeList = z.array(EvmRpcNode);

export type EvmRpcNodeList = z.infer<typeof EvmRpcNodeList>;

export function getPlaceholderNode(chain: Blockchain): EvmRpcNode {
  return {
    identifier: -1,
    name: '',
    endpoint: '',
    weight: 0,
    active: true,
    owned: true,
    blockchain: chain,
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
