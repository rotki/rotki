import { z } from 'zod';

const EthereumRpcNode = z.object({
  identifier: z.number(),
  name: z.string().nonempty(),
  endpoint: z.string(),
  owned: z.boolean(),
  weight: z.preprocess(
    weight => parseFloat(weight as string),
    z.number().nonnegative().max(100)
  ),
  active: z.boolean()
});

export type EthereumRpcNode = z.infer<typeof EthereumRpcNode>;

export const EthereumRpcNodeList = z.array(EthereumRpcNode);
export type EthereumRpcNodeList = z.infer<typeof EthereumRpcNodeList>;

export const getPlaceholderNode = (): EthereumRpcNode => ({
  identifier: -1,
  name: '',
  endpoint: '',
  weight: 0,
  active: true,
  owned: true
});
