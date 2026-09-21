import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useLocations } from '@/modules/core/common/use-locations';

interface UseBankNameReturn {
  /**
   * The name of the bank a connection's data belongs to, such as ING for a FinTS connection, or
   * the connector's name while the location has no display data yet.
   */
  bankNameOf: (connection: { location: string; connector: string }) => string;
}

export function useBankName(): UseBankNameReturn {
  const { getLocationData } = useLocations();
  const store = useBankConnectionsStore();

  const bankNameOf = ({ connector, location }: { location: string; connector: string }): string =>
    getLocationData(location)?.name ?? store.bankNameFor(connector);

  return { bankNameOf };
}
