import { blockscoutLinks } from '@shared/external-links';

type BlockscoutKey = keyof typeof blockscoutLinks;

export function isBlockscoutKey(location: string): location is BlockscoutKey {
  return location in blockscoutLinks;
}
