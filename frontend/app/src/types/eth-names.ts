import { z } from 'zod';
import { Blockchain } from '@rotki/common/lib/blockchain';

export const EthNames = z.record(z.string().nullable());

export type EthNames = z.infer<typeof EthNames>;

export const AddressBookSimplePayload = z.object({
  address: z.string(),
  blockchain: z
    .string()
    .transform(blockchain => blockchain as Blockchain)
    .nullable()
});

export type AddressBookSimplePayload = z.infer<typeof AddressBookSimplePayload>;

export const AddressBookEntry = AddressBookSimplePayload.extend({
  name: z.string()
});

export type AddressBookEntry = z.infer<typeof AddressBookEntry>;

export const AddressBookEntries = z.array(AddressBookEntry);

export type AddressBookEntries = z.infer<typeof AddressBookEntries>;

export const AddressBookLocation = z.enum(['global', 'private']);

export const AddressBookPayload = AddressBookEntry.extend({
  location: AddressBookLocation,
  blockchain: z.nativeEnum(Blockchain).nullable()
});

export type AddressBookPayload = z.infer<typeof AddressBookPayload>;

export type AddressBookLocation = z.infer<typeof AddressBookLocation>;
