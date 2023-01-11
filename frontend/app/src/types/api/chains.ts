import { z } from 'zod';

const BasicChainInfo = z.object({
  name: z.string(),
  type: z.string()
});

const EvmChainInfo = z.object({
  name: z.string(),
  type: z.literal('evm'),
  evmChainName: z.string()
});

export type EvmChainInfo = z.infer<typeof EvmChainInfo>;

export const ChainInfo = EvmChainInfo.or(BasicChainInfo);

export type ChainInfo = z.infer<typeof ChainInfo>;

export const SupportedChains = z.array(ChainInfo);

export type SupportedChains = z.infer<typeof SupportedChains>;
