import { useForm } from '@/composables/form';
import type { AddressBookSimplePayload } from '@/types/eth-names';

function defaultPayload(): AddressBookSimplePayload {
  return {
    address: '',
    blockchain: null,
  };
}

export const useAddressBookForm = createSharedComposable(() => {
  const forms = useForm<boolean>();

  const globalPayload = ref<AddressBookSimplePayload>(defaultPayload());

  const showGlobalDialog = (newPayload: AddressBookSimplePayload): void => {
    set(globalPayload, newPayload);
    forms.setOpenDialog(true);
  };

  return {
    globalPayload,
    showGlobalDialog,
    ...forms,
  };
});
