import { z } from 'zod';
import { type Blockchain } from '@rotki/common/lib/blockchain';

const EvmRpcNode = z.object({
  identifier: z.number(),
  name: z.string().min(1),
  endpoint: z.string(),
  owned: z.boolean(),
  weight: z.preprocess(
    weight => Number.parseFloat(weight as string),
    z.number().nonnegative().max(100)
  ),
  active: z.boolean(),
  blockchain: z.string().min(1)
});

export type EvmRpcNode = z.infer<typeof EvmRpcNode>;

export const EvmRpcNodeList = z.array(EvmRpcNode);

export type EvmRpcNodeList = z.infer<typeof EvmRpcNodeList>;

export const getPlaceholderNode = (chain: Blockchain): EvmRpcNode => ({
  identifier: -1,
  name: '',
  endpoint: '',
  weight: 0,
  active: true,
  owned: true,
  blockchain: chain
});
