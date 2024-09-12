import { camelCase } from 'lodash-es';
import type { EthereumValidator, EthereumValidatorRequestPayload } from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';

function filterValidator(
  validator: EthereumValidator,
  filters: { index?: string[]; publicKey?: string[]; status?: string[] },
): boolean {
  const {
    index: indexFilter,
    publicKey: publicKeyFilter,
    status: statusFilter,
  } = filters;

  const matches: { name: keyof typeof filters; matches: boolean }[] = [];

  if (indexFilter && indexFilter.length > 0)
    matches.push({ name: 'index', matches: indexFilter.some(item => includes(validator.index.toString(), item)) });

  if (publicKeyFilter && publicKeyFilter.length > 0)
    matches.push({ name: 'publicKey', matches: publicKeyFilter.some(item => includes(validator.publicKey.toString(), item)) });

  if (statusFilter && statusFilter.length > 0)
    matches.push({ name: 'status', matches: statusFilter.includes(validator.status) });

  return matches.length > 0 && matches.every(match => match.matches);
}

export function sortAndFilterValidators(
  validators: EthereumValidator[],
  params: EthereumValidatorRequestPayload,
): Collection<EthereumValidator> {
  const {
    offset,
    limit,
    orderByAttributes = [],
    ascending = [],
    index,
    publicKey,
    status,
  } = params;

  const hasFilter = isFilterEnabled(index)
    || isFilterEnabled(publicKey)
    || isFilterEnabled(status);

  const filtered = !hasFilter
    ? validators
    : validators.filter(validator => filterValidator(validator, {
      index,
      publicKey,
      status,
    }));

  const sorted = orderByAttributes.length <= 0
    ? filtered
    : filtered.sort((a, b) => {
      for (const [i, attr] of orderByAttributes.entries()) {
        const key = camelCase(attr) as keyof EthereumValidator;
        const asc = ascending[i];

        const order = sortBy(a[key], b[key], asc);
        if (order)
          return order;
      }
      return 0;
    });

  return {
    data: sorted.slice(offset, offset + limit),
    limit: -1,
    total: validators.length,
    found: sorted.length,
    totalUsdValue: sum(filtered),
  };
}
