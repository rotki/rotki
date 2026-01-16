import type { PaginationRequestPayload } from '@/types/common';
import { z } from 'zod/v4';

export enum NewDetectedTokenKind {
  EVM = 'evm',
  SOLANA = 'solana',
}

export const NewDetectedToken = z.object({
  detectedAt: z.number().default(() => Date.now()),
  isIgnored: z.boolean().optional(),
  seenDescription: z.string().nullish(),
  seenTxReference: z.string().nullish(),
  tokenIdentifier: z.string(),
  tokenKind: z.enum(NewDetectedTokenKind).default(NewDetectedTokenKind.EVM),
});

export type NewDetectedToken = z.infer<typeof NewDetectedToken>;

export type NewDetectedTokenInput = z.input<typeof NewDetectedToken>;

export const NewDetectedTokens = z.array(NewDetectedToken);

export type NewDetectedTokens = z.infer<typeof NewDetectedTokens>;

export interface NewDetectedTokenRecord extends NewDetectedToken {
  id?: number;
}

export interface NewDetectedTokensFilterParams {
  tokenKind?: NewDetectedTokenKind;
}

export interface NewDetectedTokensRequestPayload extends PaginationRequestPayload<NewDetectedToken>, NewDetectedTokensFilterParams {}
