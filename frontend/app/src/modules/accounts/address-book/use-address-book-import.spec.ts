import { createMockCSV } from '@test/mocks/file';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAddressBookImport } from '@/modules/accounts/address-book/use-address-book-import';
import { useAddressBookOperations } from '@/modules/accounts/address-book/use-address-book-operations';
import { CSVMissingHeadersError, useCsvImportExport } from '@/modules/core/common/use-csv-import-export';

const mockNotifyError = vi.fn();

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn((): { notifyError: typeof mockNotifyError } => ({
    notifyError: mockNotifyError,
  })),
}));

vi.mock('@/modules/accounts/address-book/use-address-book-operations', () => ({
  useAddressBookOperations: vi.fn().mockReturnValue({
    addAddressBook: vi.fn().mockReturnValue(true),
  }),
}));

describe('useAddressBookImport', () => {
  let addressBookOps: ReturnType<typeof useAddressBookOperations>;
  setActivePinia(createPinia());
  const { parseCSV } = useCsvImportExport();

  beforeEach(() => {
    addressBookOps = useAddressBookOperations();
    vi.clearAllMocks();
  });

  it('should handle rows with no location (defaults to private)', async () => {
    const { importAddressBook } = useAddressBookImport();
    const mockFile = createMockCSV([
      'address,blockchain,name',
      'address1,eth,Name1',
      'address2,btc,Name2',
    ]);

    const csvContent = await mockFile.text();
    const parsedData = parseCSV(csvContent);

    expect(parsedData).toEqual([
      { address: 'address1', blockchain: 'eth', name: 'Name1' },
      { address: 'address2', blockchain: 'btc', name: 'Name2' },
    ]);

    const result = await importAddressBook(mockFile);
    await flushPromises();

    expect(result).toBe(2);
    expect(addressBookOps.addAddressBook).toHaveBeenCalledWith('private', [
      { address: 'address1', blockchain: 'eth', name: 'Name1' },
      { address: 'address2', blockchain: 'btc', name: 'Name2' },
    ], true);
  });

  it('should throw an error when rows are missing address or name', async () => {
    const { importAddressBook } = useAddressBookImport();

    const mockFile = createMockCSV([
      'address,blockchain,name',
      ',eth,Name1', // Missing address
      'address2,btc,', // Missing name
    ]);

    const result = await importAddressBook(mockFile);
    await flushPromises();

    expect(result).toBe(0);
    expect(addressBookOps.addAddressBook).not.toHaveBeenCalled();
    expect(mockNotifyError).toHaveBeenCalledWith(
      'address_book.import.title',
      expect.stringMatching(/^address_book\.import\.import_error\.message.*/),
    );
  });

  it('should throw an error if headers are missing', async () => {
    const { importAddressBook } = useAddressBookImport();

    const mockFile = createMockCSV(['missing headers']); // Invalid CSV

    let error;
    try {
      parseCSV(await mockFile.text(), {
        requiredHeaders: ['address', 'name'],
      });
    }
    catch (error_) {
      error = error_;
    }

    expect(error).toBeInstanceOf(CSVMissingHeadersError);

    const result = await importAddressBook(mockFile);
    await flushPromises();

    expect(result).toBe(0);
    expect(mockNotifyError).toHaveBeenCalledWith(
      'address_book.import.title',
      expect.stringMatching(/^address_book\.import\.import_error\.invalid_format\.*/),
    );
  });

  it('should handle rows with location specified', async () => {
    const { importAddressBook } = useAddressBookImport();

    const mockFile = createMockCSV([
      'address,blockchain,name,location',
      'address1,eth,Name1,private',
      'address2,btc,Name2,global',
    ]);

    const result = await importAddressBook(mockFile);
    await flushPromises();

    expect(result).toBe(2);
    expect(addressBookOps.addAddressBook).toHaveBeenCalledWith('private', [
      { address: 'address1', blockchain: 'eth', name: 'Name1' },
    ], true);
    expect(addressBookOps.addAddressBook).toHaveBeenCalledWith('global', [
      { address: 'address2', blockchain: 'btc', name: 'Name2' },
    ], true);
  });

  it('should ignore invalid location values', async () => {
    const { importAddressBook } = useAddressBookImport();

    const mockFile = createMockCSV([
      'address,blockchain,name,location',
      'address1,eth,Name1,invalid_location',
      'address2,btc,Name2,private',
    ]);

    const result = await importAddressBook(mockFile);
    await flushPromises();

    expect(result).toBe(1);
    expect(addressBookOps.addAddressBook).toHaveBeenCalledTimes(1);
    expect(addressBookOps.addAddressBook).toHaveBeenCalledWith('private', [
      { address: 'address2', blockchain: 'btc', name: 'Name2' },
    ], true);
  });
});
