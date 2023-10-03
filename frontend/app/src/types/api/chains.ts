import { z } from 'zod';

const BasicChainInfo = z.object({
  id: z.string(),
  name: z.string(),
  type: z.string(),
  image: z.string()
});

const SubstrateChainInfo = BasicChainInfo.extend({
  type: z.literal('substrate'),
  nativeToken: z.string().optional()
});

export type SubstrateChainInfo = z.infer<typeof SubstrateChainInfo>;

const EvmChainInfo = BasicChainInfo.extend({
  type: z.literal('evm'),
  evmChainName: z.string(),
  nativeToken: z.string().optional()
});

export type EvmChainInfo = z.infer<typeof EvmChainInfo>;

export const ChainInfo = EvmChainInfo.or(SubstrateChainInfo)
  .or(BasicChainInfo)
  .transform(obj => ({
    ...obj,
    name: toCapitalCase(obj.name)
  }));

export type ChainInfo = z.infer<typeof ChainInfo>;

export const SupportedChains = z.array(ChainInfo);

export type SupportedChains = z.infer<typeof SupportedChains>;

export const EvmChainEntry = z.object({
  id: z.number(),
  name: z.string(),
  label: z.string()
});

export const EvmChainEntries = z.array(EvmChainEntry);

export type EvmChainEntries = z.infer<typeof EvmChainEntries>;
