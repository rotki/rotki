import { z } from 'zod';

export const EthNames = z.record(z.string().nullable());
export type EthNames = z.infer<typeof EthNames>;
export const EthNamesEntry = z.object({
  address: z.string(),
  name: z.string()
});
export type EthNamesEntry = z.infer<typeof EthNamesEntry>;
export const EthNamesEntries = z.array(EthNamesEntry);
export type EthNamesEntries = z.infer<typeof EthNamesEntries>;
export const EthAddressBookLocation = z.enum(['global', 'private']);
export const EthNamesPayload = EthNamesEntry.merge(
  z.object({
    location: EthAddressBookLocation
  })
);
export type EthNamesPayload = z.infer<typeof EthNamesPayload>;
export type EthAddressBookLocation = z.infer<typeof EthAddressBookLocation>;
