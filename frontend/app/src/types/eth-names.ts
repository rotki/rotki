import type { PaginationRequestPayload } from '@/types/common';
import { Blockchain } from '@rotki/common';
import { z } from 'zod/v4';
import { CollectionCommonFields } from '@/types/collection';

export const EthNamesSchema = z.record(z.string(), z.string().nullable());

export type EthNames = z.infer<typeof EthNamesSchema>;

const BlockchainEnum = z.enum(Blockchain);

export const AddressNameRequestPayload = z.object({
  address: z.string(),
  blockchain: BlockchainEnum,
});

export type AddressNameRequestPayload = z.infer<typeof AddressNameRequestPayload>;

export const AddressBookSimplePayload = AddressNameRequestPayload.extend({
  blockchain: z.string().nullable(),
});

export type AddressBookSimplePayload = z.infer<typeof AddressBookSimplePayload>;

export const AddressBookInfo = z.object({
  name: z.string(),
  source: z.string().optional(),
});

export const AddressBookEntry = z.object({
  ...AddressBookSimplePayload.shape,
  ...AddressBookInfo.shape,
});

export type AddressBookEntry = z.infer<typeof AddressBookEntry>;

export const AddressBookEntriesSchema = z.array(AddressBookEntry);

export type AddressBookEntries = z.infer<typeof AddressBookEntriesSchema>;

export const AddressBookCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(AddressBookEntry),
});

export type AddressBookCollectionResponse = z.infer<typeof AddressBookCollectionResponse>;

export const AddressBookLocation = z.enum(['global', 'private']);

export const AddressBookPayload = AddressBookEntry.extend({
  location: AddressBookLocation,
});

export type AddressBookPayload = z.infer<typeof AddressBookPayload>;

export type AddressBookLocation = z.infer<typeof AddressBookLocation>;

export interface AddressBookRequestPayload extends PaginationRequestPayload<AddressBookEntry> {
  nameSubstring?: string;
  address?: string[];
  blockchain?: Blockchain;
  strictBlockchain?: boolean;
}
