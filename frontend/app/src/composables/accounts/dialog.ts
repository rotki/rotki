import { type BlockchainAccountWithBalance } from '@/types/blockchain/accounts';

type Title = {
  title: string;
  subtitle?: string;
};

const defaultTitle = (): Title => ({ title: '' });

export const useAccountDialog = createSharedComposable(() => {
  const accountToEdit: Ref<BlockchainAccountWithBalance | null> = ref(null);
  const dialogText: Ref<Title> = ref(defaultTitle());
  const openDialog: Ref<boolean> = ref(false);
  const valid: Ref<boolean> = ref(false);
  const saveFunc = ref<() => Promise<boolean>>();

  const { t } = useI18n();

  const clearDialog = async (): Promise<void> => {
    set(openDialog, false);
    setTimeout(async () => {
      set(accountToEdit, null);
    }, 300);
  };

  const createAccount = (): void => {
    set(accountToEdit, null);
    set(dialogText, {
      title: t('blockchain_balances.form_dialog.add_title')
    });
    set(openDialog, true);
  };

  const editAccount = (account: BlockchainAccountWithBalance): void => {
    set(accountToEdit, account);
    set(dialogText, {
      title: t('blockchain_balances.form_dialog.edit_title'),
      subtitle: t('blockchain_balances.form_dialog.edit_subtitle')
    });
    set(openDialog, true);
  };

  const setSave = (func: () => Promise<boolean>) => {
    set(saveFunc, func);
  };

  const save = async () => {
    const method = get(saveFunc);
    if (!method) {
      logger.error('save method not set');
      return;
    }

    const success = await method();
    if (success) {
      await clearDialog();
    }
  };

  return {
    dialogText,
    openDialog,
    accountToEdit,
    valid,
    setSave,
    save,
    createAccount,
    editAccount,
    clearDialog
  };
});
