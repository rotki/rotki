import type {
  EthereumValidator,
  EthereumValidatorRequestPayload,
} from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import { camelCase } from 'es-toolkit';
import { sum } from '@/utils/balances';
import { includes, isFilterEnabled, sortBy } from '@/utils/blockchain/accounts/common';
import { bigNumberSum } from '@/utils/calculation';

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
    matches.push({ matches: indexFilter.some(item => includes(validator.index.toString(), item)), name: 'index' });

  if (publicKeyFilter && publicKeyFilter.length > 0)
    matches.push({ matches: publicKeyFilter.some(item => includes(validator.publicKey.toString(), item)), name: 'publicKey' });

  if (statusFilter && statusFilter.length > 0)
    matches.push({ matches: statusFilter.includes(validator.status), name: 'status' });

  return matches.length > 0 && matches.every(match => match.matches);
}

export function sortAndFilterValidators(
  validators: EthereumValidator[],
  params: EthereumValidatorRequestPayload,
): Collection<EthereumValidator> {
  const {
    ascending = [],
    index,
    limit,
    offset,
    orderByAttributes = [],
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

  const totalAmount = bigNumberSum(filtered.map(account => account.amount));

  return {
    data: sorted.slice(offset, offset + limit),
    found: sorted.length,
    limit: -1,
    total: validators.length,
    totalValue: sum(filtered),
    totalAmount,
  };
}
