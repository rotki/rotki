import { z } from 'zod';
import { groupBy, omit } from 'lodash-es';
import { logger } from '@/utils/logging.ts';
import { CSVMissingHeadersError, useCsvImportExport } from '@/composables/common/use-csv-import-export.ts';
import { useNotificationsStore } from '@/store/notifications';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names.ts';

const CSVRow = z.object({
  address: z.string(),
  blockchain: z.string().nullish().transform(item => item || null),
  location: z.string().optional().transform(item => item || 'private'),
  name: z.string(),
});

const CSVSchema = z.array(CSVRow);

type CSVRow = z.infer<typeof CSVRow>;

interface UseAddressBookImport {
  importAddressBook: (file: File) => Promise<number>;
}

export function useAddressBookImport(): UseAddressBookImport {
  const { parseCSV } = useCsvImportExport();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();
  const { addAddressBook } = useAddressesNamesStore();

  async function handleAddressBookImport(rows: CSVRow[]): Promise<number> {
    const groupedByLocation = groupBy(rows, 'location');
    const locationPromises: { promise: Promise<boolean>; rowCount: number }[] = [];

    Object.entries(groupedByLocation)
      .forEach(([location, items]) => {
        if (location === 'global' || location === 'private') {
          const formattedRows = items.map(item => omit(item, 'location'));
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
      const names = CSVSchema.parse(parseCSV(csvContent));
      const length = await handleAddressBookImport(names);
      return length;
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
