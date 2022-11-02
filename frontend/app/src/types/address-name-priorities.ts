import {z} from "zod";

export enum AddressNamePriority {
  BLOCKCHAIN_ACCOUNT = 'blockchain_account',
  ENS_NAMES = 'ens_names',
  ETHEREUM_TOKENS = 'ethereum_tokens',
  GLOBAL_ADDRESSBOOK = 'global_addressbook',
  HARDCODED_MAPPINGS = 'hardcoded_mappings',
  PRIVATE_ADDRESSBOOK = 'private_addressbook'
}

export const AddressNamePriorityEnum = z.nativeEnum(AddressNamePriority);
export type AddressNamePriorityEnum = z.infer<typeof AddressNamePriorityEnum>;

export const BLOCKCHAIN_ACCOUNT_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: AddressNamePriority.BLOCKCHAIN_ACCOUNT
};

export const ENS_NAMES_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: AddressNamePriority.ENS_NAMES
};

export const ETHEREUM_TOKENS_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: AddressNamePriority.ETHEREUM_TOKENS
};

export const GLOBAL_ADDRESSBOOK_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: AddressNamePriority.GLOBAL_ADDRESSBOOK
};

export const HARDCODED_MAPPINGS_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: AddressNamePriority.HARDCODED_MAPPINGS
};

export const PRIVATE_ADDRESSBOOK_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: AddressNamePriority.PRIVATE_ADDRESSBOOK
};
