import type { ComputedRef } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { NewlyDetectedFilterKeys } from '@/modules/assets/detection/use-newly-detected-filter';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { NewDetectedTokenKind } from './types';

/** The two kinds read as their chain families rather than as the wire tokens `evm`/`solana`. */
const kindLabels = new Map<string, string>([
  [NewDetectedTokenKind.EVM, 'EVM'],
  [NewDetectedTokenKind.SOLANA, 'Solana'],
]);

const kinds: string[] = Object.values(NewDetectedTokenKind);

/**
 * The pill-bar field for the newly detected assets table.
 *
 * Reactive rather than a plain list: with no solana account every detected token is an evm one, so
 * the field would offer a filter that cannot narrow anything. The select this replaces stayed on
 * screen in that case, as a dropdown with a single option.
 *
 * The absent pill is what "all types" meant in that select, so there is no value standing for it.
 */
export function useNewlyDetectedFields(): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  const { isSolanaChains } = useSupportedChains();
  const { addresses } = useAccountAddresses();

  const hasSolanaAccounts = computed<boolean>(() =>
    Object.entries(get(addresses)).some(([chain, addrs]) => isSolanaChains(chain) && addrs.length > 0),
  );

  return computed<FieldDef[]>(() => get(hasSolanaAccounts)
    ? [toMatchFieldDef({
        key: NewlyDetectedFilterKeys.TOKEN_KIND,
        label: (): string => t('asset_table.newly_detected.token_type'),
        multiple: false,
        resolveLabel: (value: string): string => kindLabels.get(value) ?? value,
        suggest: (): string[] => kinds,
        validate: (value: string): boolean => kinds.includes(value),
      })]
    : []);
}
