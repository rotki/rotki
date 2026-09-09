import type { Blockchain } from '@rotki/common';
import { z } from 'zod';

const BlockchainRpcNode = z.object({
  active: z.boolean(),
  blockchain: z.string().min(1),
  cooldownUntil: z.number().nullable().optional(),
  endpoint: z.string(),
  identifier: z.number(),
  isArchive: z.boolean().optional(),
  name: z.string().min(1),
  owned: z.boolean(),
  runtimeStatus: z.enum(['ready', 'cooling_down']).optional(),
  weight: z.preprocess(weight => Number.parseFloat(String(weight)), z.number().nonnegative().max(100)),
});

export type BlockchainRpcNode = z.infer<typeof BlockchainRpcNode>;

export const BlockchainRpcNodeList = z.array(BlockchainRpcNode);

export type BlockchainRpcNodeList = z.infer<typeof BlockchainRpcNodeList>;

/**
 * The fields the backend add/edit schemas accept. Everything else the GET response carries is
 * read-only runtime state, and marshmallow rejects it with `Unknown field`. Parsing a node through
 * these schemas keeps the payload an allowlist: fields the server grows later are dropped without
 * anyone having to maintain a list of them here.
 */
export const BlockchainRpcNodeEditPayload = BlockchainRpcNode.pick({
  active: true,
  blockchain: true,
  endpoint: true,
  identifier: true,
  name: true,
  owned: true,
  weight: true,
});

export const BlockchainRpcNodeAddPayload = BlockchainRpcNodeEditPayload.omit({ identifier: true });

/**
 * What a connect attempt reports back.
 *
 * @remarks
 * The backend connects synchronously and answers with the nodes it could not reach, so an empty
 * `errors` is the only success. A node that answers on the wrong chain is reported here too.
 */
export const RpcNodeConnectResult = z.object({
  errors: z.array(z.object({
    error: z.string(),
    name: z.string(),
  })),
});

export type RpcNodeConnectResult = z.infer<typeof RpcNodeConnectResult>;

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
