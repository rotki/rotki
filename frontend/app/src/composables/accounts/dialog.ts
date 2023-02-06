import { type Ref } from 'vue';
import { logger } from '@/utils/logging';
import { type BlockchainAccountWithBalance } from '@/types/accounts';

type Title = {
  title: string;
  subtitle?: string;
};

const defaultTitle = (): Title => ({ title: '' });

export const useAccountDialog = createSharedComposable(() => {
  const accountToEdit: Ref<BlockchainAccountWithBalance | null> = ref(null);
  const dialogText = ref<Title>(defaultTitle());
  const openDialog = ref(false);
  const valid = ref(false);
  const saveFunc = ref<Function>();

  const { tc } = useI18n();

  const clearDialog = async (): Promise<void> => {
    set(openDialog, false);
    setTimeout(async () => {
      set(accountToEdit, null);
    }, 300);
  };

  const createAccount = (): void => {
    set(accountToEdit, null);
    set(dialogText, {
      title: tc('blockchain_balances.form_dialog.add_title')
    });
    set(openDialog, true);
  };

  const editAccount = (account: BlockchainAccountWithBalance): void => {
    set(accountToEdit, account);
    set(dialogText, {
      title: tc('blockchain_balances.form_dialog.edit_title'),
      subtitle: tc('blockchain_balances.form_dialog.edit_subtitle')
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
