import { groupBy, omit } from 'es-toolkit';
import { z } from 'zod/v4';
import { useAddressBookOperations } from '@/modules/accounts/address-book/use-address-book-operations';
import { logger } from '@/modules/core/common/logging/logging';
import { CSVMissingHeadersError, useCsvImportExport } from '@/modules/core/common/use-csv-import-export';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

const CSVRow = z.object({
  address: z.string().min(1),
  blockchain: z.string().nullish().transform(item => item || null),
  location: z.string().optional().transform(item => item || 'private'),
  name: z.string().min(1),
});

const CSVSchema = z.array(CSVRow);

type CSVRow = z.infer<typeof CSVRow>;

interface UseAddressBookImport {
  importAddressBook: (file: File) => Promise<number>;
}

export function useAddressBookImport(): UseAddressBookImport {
  const { parseCSV } = useCsvImportExport();
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
  const { addAddressBook } = useAddressBookOperations();

  async function handleAddressBookImport(rows: CSVRow[]): Promise<number> {
    const groupedByLocation = groupBy(rows, item => item.location);
    const locationPromises: { promise: Promise<boolean>; rowCount: number }[] = [];

    Object.entries(groupedByLocation)
      .forEach(([location, items]) => {
        if (location === 'global' || location === 'private') {
          const formattedRows = items.map(item => omit(item, ['location']));
          if (formattedRows.length > 0) {
            locationPromises.push({
              promise: addAddressBook(location, formattedRows, true),
              rowCount: formattedRows.length,
            });
          }
        }
      });

    const results = await Promise.all(locationPromises.map(async x => x.promise));

    return results.reduce((total, success, index) =>
      success ? total + locationPromises[index].rowCount : total, 0);
  }

  async function importAddressBook(file: File): Promise<number> {
    try {
      const csvContent = await file.text();
      const names = CSVSchema.parse(parseCSV(csvContent, {
        requiredHeaders: ['address', 'name'],
      }));
      return await handleAddressBookImport(names);
    }
    catch (error) {
      const message = error instanceof CSVMissingHeadersError
        ? t('address_book.import.import_error.invalid_format')
        : t('address_book.import.import_error.message', {
            error,
          });
      logger.error(message);
      notifyError(t('address_book.import.title'), message);
      return 0;
    }
  }

  return {
    importAddressBook,
  };
}
