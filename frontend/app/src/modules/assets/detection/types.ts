import type { PaginationRequestPayload } from '@/modules/core/common/common-types';
import { z } from 'zod';

export enum NewDetectedTokenKind {
  EVM = 'evm',
  SOLANA = 'solana',
}

const newDetectedTokenKinds: string[] = Object.values(NewDetectedTokenKind);

/** Whether a raw value (a filter the url can carry) names a kind the query knows. */
export function isNewDetectedTokenKind(value: string | undefined): value is NewDetectedTokenKind {
  return value !== undefined && newDetectedTokenKinds.includes(value);
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

interface NewDetectedTokensFilterParams {
  tokenKind?: NewDetectedTokenKind;
}

export interface NewDetectedTokensRequestPayload extends PaginationRequestPayload<NewDetectedToken>, NewDetectedTokensFilterParams {}
