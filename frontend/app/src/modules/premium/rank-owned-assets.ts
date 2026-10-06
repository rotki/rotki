import type { AssetBalance } from '@rotki/common';

/**
 * Orders owned asset identifiers by their current value, largest first. Assets with no current
 * balance follow, in the order they came in: the owned list spans every asset ever held, and most
 * of it is gone or worthless today.
 */
export function rankOwnedAssets(owned: string[], balances: Pick<AssetBalance, 'asset' | 'value'>[]): string[] {
  const valueOf = new Map(balances.map(({ asset, value }) => [asset, value]));
  const held = owned.flatMap((asset) => {
    const value = valueOf.get(asset);
    return value ? [{ asset, value }] : [];
  });
  held.sort((a, b) => b.value.comparedTo(a.value) ?? 0);

  return [...held.map(({ asset }) => asset), ...owned.filter(asset => !valueOf.has(asset))];
}
