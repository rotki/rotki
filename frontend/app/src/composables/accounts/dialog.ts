import type { BlockchainAccountWithBalance } from '@/types/blockchain/accounts';

interface Title {
  title: string;
  subtitle?: string;
}

const defaultTitle = (): Title => ({ title: '' });

export const useAccountDialog = createSharedComposable(() => {
  const accountToEdit: Ref<BlockchainAccountWithBalance | null> = ref(null);
  const dialogText: Ref<Title> = ref(defaultTitle());
  const openDialog: Ref<boolean> = ref(false);

  const { t } = useI18n();

  const clearDialog = (): void => {
    set(openDialog, false);
    setTimeout(() => {
      set(accountToEdit, null);
    }, 300);
  };

  const createAccount = (): void => {
    set(accountToEdit, null);
    set(dialogText, {
      title: t('blockchain_balances.form_dialog.add_title'),
    });
    set(openDialog, true);
  };

  const editAccount = (account: BlockchainAccountWithBalance): void => {
    set(accountToEdit, account);
    set(dialogText, {
      title: t('blockchain_balances.form_dialog.edit_title'),
      subtitle: t('blockchain_balances.form_dialog.edit_subtitle'),
    });
    set(openDialog, true);
  };

  const {
    valid,
    setValidation,
    setSubmitFunc,
    setPostSubmitFunc,
    trySubmit,
    submitting,
  } = useForm<boolean>();

  return {
    dialogText,
    openDialog,
    accountToEdit,
    valid,
    setValidation,
    trySubmit,
    setSubmitFunc,
    setPostSubmitFunc,
    createAccount,
    editAccount,
    clearDialog,
    submitting,
  };
});
