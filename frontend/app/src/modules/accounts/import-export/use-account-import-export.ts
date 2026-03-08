import { useAccountExport } from '@/modules/accounts/import-export/use-account-export';
import { useAccountImport } from '@/modules/accounts/import-export/use-account-import';

interface UseAccountImportExportReturn {
  exportAccounts: () => void;
  importAccounts: (file: File) => Promise<void>;
}

export function useAccountImportExport(): UseAccountImportExportReturn {
  const { exportAccounts } = useAccountExport();
  const { importAccounts } = useAccountImport();

  return {
    exportAccounts,
    importAccounts,
  };
}
