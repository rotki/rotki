import { CSVMissingHeadersError, useCsvImportExport } from '@/composables/common/use-csv-import-export';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useNotificationsStore } from '@/store/notifications';
import { logger } from '@/utils/logging';
import { groupBy, omit } from 'es-toolkit';
import { z } from 'zod/v4';

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
  const { notify } = useNotificationsStore();
  const { t } = useI18n({ useScope: 'global' });
  const { addAddressBook } = useAddressesNamesStore();

  async function handleAddressBookImport(rows: CSVRow[]): Promise<number> {
    const groupedByLocation = groupBy(rows, item => item.location);
    const locationPromises: { promise: Promise<boolean>; rowCount: number }[] = [];

    Object.entries(groupedByLocation)
      .forEach(([location, items]) => {
        if (location === 'global' || location === 'private') {
          const formattedRows = items.map(item => omit(item, ['location']));
          if (formattedRows.length > 0) {
            locationPromises.push({
              promise: addAddressBook(location, formattedRows),
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
      notify({
        display: true,
        message,
        title: t('address_book.import.title'),
      });
      return 0;
    }
  }

  return {
    importAddressBook,
  };
}
