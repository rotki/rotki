import type { AddressBookPayload, AddressBookSimplePayload } from '@/types/eth-names';

function defaultPayload(): AddressBookPayload {
  return {
    address: '',
    blockchain: null,
    location: 'private',
    name: '',
  };
}

export const useAddressBookForm = createSharedComposable(() => {
  const openDialog = ref<boolean>(false);

  const globalPayload = ref<AddressBookPayload>(defaultPayload());

  const showGlobalDialog = (newPayload: AddressBookSimplePayload & { name?: string }): void => {
    set(globalPayload, {
      ...get(globalPayload),
      ...newPayload,
    });
    set(openDialog, true);
  };

  return {
    globalPayload,
    openDialog,
    showGlobalDialog,
  };
});
