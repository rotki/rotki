import { toCapitalCase } from '@rotki/common';
import { z } from 'zod/v4';

const BasicChainInfo = z.object({
  id: z.string(),
  image: z.string(),
  name: z.string(),
  type: z.string(),
});

const SubstrateChainInfo = BasicChainInfo.extend({
  nativeToken: z.string().optional(),
  type: z.literal('substrate'),
});

export type SubstrateChainInfo = z.infer<typeof SubstrateChainInfo>;

const EvmLikeChainInfo = BasicChainInfo.extend({
  nativeToken: z.string().optional(),
  type: z.literal('evmlike'),
});

export type EvmLikeChainInfo = z.infer<typeof EvmLikeChainInfo>;

const EvmChainInfo = BasicChainInfo.extend({
  evmChainName: z.string(),
  nativeToken: z.string().optional(),
  type: z.literal('evm'),
});

export type EvmChainInfo = z.infer<typeof EvmChainInfo>;

export const ChainInfo = EvmChainInfo.or(SubstrateChainInfo)
  .or(EvmLikeChainInfo)
  .or(BasicChainInfo)
  .transform(obj => ({
    ...obj,
    name: toCapitalCase(obj.name),
  }));

export type ChainInfo = z.infer<typeof ChainInfo>;

export const SupportedChains = z.array(ChainInfo);

export type SupportedChains = z.infer<typeof SupportedChains>;

const EvmChainEntry = z.object({
  id: z.number(),
  label: z.string(),
  name: z.string(),
});

export const EvmChainEntries = z.array(EvmChainEntry);

export type EvmChainEntries = z.infer<typeof EvmChainEntries>;
