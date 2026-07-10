import { z } from 'zod';

export enum AddressNamePriority {
  BLOCKCHAIN_ACCOUNT = 'blockchain_account',
  ENS_NAMES = 'ens_names',
  ETHEREUM_TOKENS = 'ethereum_tokens',
  GLOBAL_ADDRESSBOOK = 'global_addressbook',
  GNS_NAMES = 'gns_names',
  HARDCODED_MAPPINGS = 'hardcoded_mappings',
  PRIVATE_ADDRESSBOOK = 'private_addressbook',
}

export const AddressNamePriorityEnum = z.enum(AddressNamePriority);

export type AddressNamePriorityEnum = z.infer<typeof AddressNamePriorityEnum>;
