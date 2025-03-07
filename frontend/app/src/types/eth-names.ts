import type { PaginationRequestPayload } from '@/types/common';
import { CollectionCommonFields } from '@/types/collection';
import { Blockchain } from '@rotki/common';
import { z } from 'zod';

export const EthNames = z.record(z.string().nullable());

export type EthNames = z.infer<typeof EthNames>;

const BlockchainEnum = z.nativeEnum(Blockchain);

export const AddressNameRequestPayload = z.object({
  address: z.string(),
  blockchain: BlockchainEnum,
});

export type AddressNameRequestPayload = z.infer<typeof AddressNameRequestPayload>;

export const AddressBookSimplePayload = AddressNameRequestPayload.extend({
  blockchain: z.string().nullable(),
});

export type AddressBookSimplePayload = z.infer<typeof AddressBookSimplePayload>;

export const AddressBookEntry = AddressBookSimplePayload.extend({
  name: z.string(),
});

export type AddressBookEntry = z.infer<typeof AddressBookEntry>;

export const AddressBookEntries = z.array(AddressBookEntry);

export type AddressBookEntries = z.infer<typeof AddressBookEntries>;

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
}
