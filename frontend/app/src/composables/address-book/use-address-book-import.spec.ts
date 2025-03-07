import { useAddressBookImport } from '@/composables/address-book/use-address-book-import';
import { CSVMissingHeadersError, useCsvImportExport } from '@/composables/common/use-csv-import-export';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useNotificationsStore } from '@/store/notifications';
import { createMockCSV } from '@test/mocks/file';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mocks
vi.mock('@/store/notifications', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    notify: vi.fn(),
  }),
}));

vi.mock('@/store/blockchain/accounts/addresses-names', () => ({
  useAddressesNamesStore: vi.fn().mockReturnValue({
    addAddressBook: vi.fn().mockReturnValue(true),
  }),
}));

describe('useAddressBookImport', () => {
  let addressesNameStore: ReturnType<typeof useAddressesNamesStore>;
  let notificationStore: ReturnType<typeof useNotificationsStore>;
  setActivePinia(createPinia());
  const { parseCSV } = useCsvImportExport();

  beforeEach(() => {
    addressesNameStore = useAddressesNamesStore();
    notificationStore = useNotificationsStore();
    vi.clearAllMocks();
  });

  it('handles rows with no location (defaults to private)', async () => {
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
    expect(addressesNameStore.addAddressBook).toHaveBeenCalledWith('private', [
      { address: 'address1', blockchain: 'eth', name: 'Name1' },
      { address: 'address2', blockchain: 'btc', name: 'Name2' },
    ]);
  });

  it('throws an error when rows are missing address or name', async () => {
    const { importAddressBook } = useAddressBookImport();

    const mockFile = createMockCSV([
      'address,blockchain,name',
      ',eth,Name1', // Missing address
      'address2,btc,', // Missing name
    ]);

    const result = await importAddressBook(mockFile);
    await flushPromises();

    expect(result).toBe(0);
    expect(addressesNameStore.addAddressBook).not.toHaveBeenCalled();
    expect(notificationStore.notify).toHaveBeenCalledWith({
      display: true,
      message: expect.stringMatching(/^address_book\.import\.import_error\.message.*/),
      title: 'address_book.import.title',
    });
  });

  it('throws an error if headers are missing', async () => {
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
    expect(notificationStore.notify).toHaveBeenCalledWith({
      display: true,
      message: expect.stringMatching(/^address_book\.import\.import_error\.invalid_format\.*/),
      title: 'address_book.import.title',
    });
  });

  it('handles rows with location specified', async () => {
    const { importAddressBook } = useAddressBookImport();

    const mockFile = createMockCSV([
      'address,blockchain,name,location',
      'address1,eth,Name1,private',
      'address2,btc,Name2,global',
    ]);

    const result = await importAddressBook(mockFile);
    await flushPromises();

    expect(result).toBe(2);
    expect(addressesNameStore.addAddressBook).toHaveBeenCalledWith('private', [
      { address: 'address1', blockchain: 'eth', name: 'Name1' },
    ]);
    expect(addressesNameStore.addAddressBook).toHaveBeenCalledWith('global', [
      { address: 'address2', blockchain: 'btc', name: 'Name2' },
    ]);
  });

  it('ignores invalid location values', async () => {
    const { importAddressBook } = useAddressBookImport();

    const mockFile = createMockCSV([
      'address,blockchain,name,location',
      'address1,eth,Name1,invalid_location',
      'address2,btc,Name2,private',
    ]);

    const result = await importAddressBook(mockFile);
    await flushPromises();

    expect(result).toBe(1);
    expect(addressesNameStore.addAddressBook).toHaveBeenCalledTimes(1);
    expect(addressesNameStore.addAddressBook).toHaveBeenCalledWith('private', [
      { address: 'address2', blockchain: 'btc', name: 'Name2' },
    ]);
  });
});
