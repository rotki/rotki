import { z } from 'zod';

const EthereumRpcNode = z.object({
  name: z.string().nonempty(),
  endpoint: z.string(),
  owned: z.boolean(),
  weight: z.number().nonnegative().max(100),
  active: z.boolean()
});

export type EthereumRpcNode = z.infer<typeof EthereumRpcNode>;

export const EthereumRpcNodeList = z.array(EthereumRpcNode);
export type EthereumRpcNodeList = z.infer<typeof EthereumRpcNodeList>;

export const getPlaceholderNode = (): EthereumRpcNode => ({
  name: '',
  endpoint: '',
  weight: 0,
  active: true,
  owned: true
});
