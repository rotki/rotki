const CLAIM_PAGES = new Map<string, string>([
  ['lido', 'https://stake.lido.fi/withdrawals/claim'],
  ['venice', 'https://venice.ai/token'],
]);

/** Where a protocol's withdrawals are claimed, when it has such a page. */
export function claimPageUrl(protocol: string): string | undefined {
  return CLAIM_PAGES.get(protocol);
}
