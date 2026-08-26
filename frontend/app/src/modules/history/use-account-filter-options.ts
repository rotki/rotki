import type { ComputedRef } from 'vue';
import type { SelectOption } from '@/modules/core/table/pill/ValueSelectList.vue';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useLocationLabels } from '@/modules/history/use-location-labels';
import { useScramble } from '@/modules/settings/use-scramble';

interface UseAccountFilterOptionsReturn {
  /** Checklist options for the account pill: one per tracked address, deduped across chains. */
  options: ComputedRef<SelectOption[]>;
  /** Maps an address to the primary label on the collapsed pill: tracked/ENS name, else the address. */
  resolveLabel: (address: string) => string;
  /** Maps an address to the muted secondary text on the pill, present only when a name is shown. */
  resolveCaption: (address: string) => string | undefined;
}

/**
 * The option list and pill label resolution for the history account filter, folded into the
 * pill bar as a param field. Shared by the account pill editor and the field's `resolveLabel`
 * so both render the same tracked/ENS name and honour the scramble setting.
 */
export function useAccountFilterOptions(): UseAccountFilterOptionsReturn {
  const { getAccountName, getTags, isAccountNamePending, locationLabelOptions } = useLocationLabels(() => undefined);
  const { scrambleAddress } = useScramble();

  const nameByAddress = computed<Map<string, string | undefined>>(() => {
    const map = new Map<string, string | undefined>();
    for (const item of get(locationLabelOptions)) {
      if (!map.has(item.locationLabel))
        map.set(item.locationLabel, getAccountName(item));
    }
    return map;
  });

  function shortAddress(address: string): string {
    return truncateAddress(scrambleAddress(address), 4);
  }

  function resolveLabel(address: string): string {
    return get(nameByAddress).get(address) ?? shortAddress(address);
  }

  function resolveCaption(address: string): string | undefined {
    return get(nameByAddress).get(address) ? shortAddress(address) : undefined;
  }

  const options = computed<SelectOption[]>(() => {
    const byAddress = new Map<string, SelectOption>();
    for (const item of get(locationLabelOptions)) {
      const address = item.locationLabel;
      if (byAddress.has(address))
        continue;
      const name = getAccountName(item);
      const shown = shortAddress(address);
      byAddress.set(address, {
        caption: name ? shown : undefined,
        keywords: `${address} ${name ?? ''} ${getTags(item).join(' ')}`.toLowerCase(),
        label: name ?? shown,
        loading: !name && isAccountNamePending(item),
        value: address,
      });
    }
    return [...byAddress.values()];
  });

  return {
    options,
    resolveCaption,
    resolveLabel,
  };
}
