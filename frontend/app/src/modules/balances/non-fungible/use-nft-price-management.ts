import type { DeepReadonly, Ref } from 'vue';
import type { ManualPriceFormPayload } from '@/modules/assets/prices/price-types';
import type { NonFungibleBalance } from '@/modules/balances/types/nfbalances';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

interface UseNftPriceManagementReturn {
  customPrice: DeepReadonly<Ref<ManualPriceFormPayload | null>>;
  /** Whether the NFT in the form already has a custom price, so the form edits it rather than adds one. */
  hasCustomPrice: Readonly<Ref<boolean>>;
  modelOpenPriceDialog: Ref<boolean>;
  /** For `RowActions`' `delete-confirm`, so a row's delete button asks before it emits. */
  deleteConfirm: (item: NonFungibleBalance) => { title: string; message: string };
  /** Deletes a custom price the user already confirmed. */
  deletePrice: (item: NonFungibleBalance) => Promise<void>;
  setPriceForm: (item: NonFungibleBalance) => void;
}

export function useNftPriceManagement(
  fetchData: () => Promise<void>,
): UseNftPriceManagementReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { deleteLatestPrice } = useAssetPricesApi();

  const modelOpenPriceDialog = shallowRef<boolean>(false);
  const customPrice = shallowRef<ManualPriceFormPayload | null>(null);
  const hasCustomPrice = shallowRef<boolean>(false);

  async function deletePrice(toDeletePrice: NonFungibleBalance): Promise<void> {
    try {
      await deleteLatestPrice(toDeletePrice.id);
      await fetchData();
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return;

      notifyError(
        t('assets.custom_price.delete.error.title'),
        t('assets.custom_price.delete.error.message', {
          asset: toDeletePrice.name ?? toDeletePrice.id,
        }),
      );
    }
  }

  function setPriceForm(item: NonFungibleBalance): void {
    set(hasCustomPrice, item.manuallyInput);
    set(customPrice, {
      fromAsset: item.id,
      price: item.priceInAsset.toFixed(),
      toAsset: item.priceAsset,
    });
    set(modelOpenPriceDialog, true);
  }

  function deleteConfirm(item: NonFungibleBalance): { title: string; message: string } {
    return {
      message: t('assets.custom_price.delete.message', { asset: item.name ?? item.id }),
      title: t('assets.custom_price.delete.tooltip'),
    };
  }

  return {
    customPrice: readonly(customPrice),
    deleteConfirm,
    deletePrice,
    hasCustomPrice: readonly(hasCustomPrice),
    modelOpenPriceDialog,
    setPriceForm,
  };
}
