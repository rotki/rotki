import type {
  AggregationContext,
  AssetBalanceEntries,
  ProtocolBalanceEntries,
} from '@/modules/balances/aggregation/core/aggregation-types';
import { type AssetBalanceWithPriceAndChains, Zero } from '@rotki/common';
import { pipe } from 'plainfp';
import { groupBy } from 'plainfp/arrays';
import { fromNullable, match } from 'plainfp/option';
import { addBalanceEntry } from '@/modules/balances/aggregation/core/balance-entry';
import {
  type AssetHolding,
  breakdownRows,
  emptyHolding,
  holdingRow,
  sortedProtocols,
  standaloneRow,
  toHolding,
} from '@/modules/balances/aggregation/core/rows';

interface Member {
  readonly holding: AssetHolding;
  readonly collectionId: string | undefined;
}

type CollectionMember = Member & { readonly collectionId: string };

function isInCollection(member: Member): member is CollectionMember {
  return !!member.collectionId;
}

function chainOf(identifier: string): string {
  return identifier.slice(0, Math.max(0, identifier.indexOf('/')));
}

/**
 * The only member holding a balance, when it sits on a different chain than the main asset.
 *
 * @remarks
 * Such a group shows that member under its own identifier, since heading it with the main asset
 * would name a chain the user holds nothing on.
 */
function soleHolderOnAnotherChain(mainAsset: string, holdings: readonly AssetHolding[]): AssetHolding | undefined {
  const holders = holdings.filter(holding => holding.amount.gt(0));
  if (holders.length !== 1 || chainOf(holders[0].asset) === chainOf(mainAsset))
    return undefined;

  return holders[0];
}

/** Folds a collection's members into one row headed by its main asset. */
function collapse(main: AssetHolding, holdings: readonly AssetHolding[]): AssetBalanceWithPriceAndChains {
  const soleHolder = soleHolderOnAnotherChain(main.asset, holdings);
  if (soleHolder)
    return holdingRow(soleHolder);

  let amount = Zero;
  let value = Zero;
  const perProtocol: ProtocolBalanceEntries = {};

  for (const holding of holdings) {
    amount = amount.plus(holding.amount);
    value = value.plus(holding.value);
    for (const [protocol, entry] of Object.entries(holding.perProtocol))
      addBalanceEntry(perProtocol, protocol, entry);
  }

  return {
    ...main,
    amount,
    breakdown: breakdownRows(holdings),
    perProtocol: sortedProtocols(perProtocol),
    value,
  };
}

/**
 * The rows for one collection: a single row headed by its main asset, or each member on its own
 * when the main asset is not known.
 *
 * @remarks
 * The main asset may hold no balance, in which case it is added empty to head the group.
 */
function collectionRows(
  collectionId: string,
  holdings: readonly AssetHolding[],
  context: Pick<AggregationContext, 'mainAssetOf' | 'priceOf'>,
): AssetBalanceWithPriceAndChains[] {
  return pipe(
    fromNullable(context.mainAssetOf(collectionId)),
    match({
      none: () => holdings.map(standaloneRow),
      some: (mainAsset) => {
        const held = holdings.find(holding => holding.asset === mainAsset);
        const main = held ?? emptyHolding(mainAsset, context);
        const members = held ? holdings : [...holdings, main];
        return [members.length === 1 ? standaloneRow(main) : collapse(main, members)];
      },
    }),
  );
}

/** One row per asset, with the members of each collection folded into a single row. */
export function groupByCollection(
  merged: AssetBalanceEntries,
  context: Pick<AggregationContext, 'collectionOf' | 'mainAssetOf' | 'priceOf'>,
): AssetBalanceWithPriceAndChains[] {
  const members: Member[] = Object.entries(merged).map(([asset, perProtocol]) => ({
    collectionId: context.collectionOf(asset),
    holding: toHolding(asset, perProtocol, context),
  }));

  const standalone = members.filter(member => !isInCollection(member)).map(member => standaloneRow(member.holding));
  const byCollection = groupBy(members.filter(isInCollection), member => member.collectionId);

  return [
    ...standalone,
    ...Object.entries(byCollection).flatMap(([collectionId, collected]) =>
      collectionRows(collectionId, collected.map(member => member.holding), context)),
  ];
}
