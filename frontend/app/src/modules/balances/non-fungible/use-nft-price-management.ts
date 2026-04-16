import type { Ref } from 'vue';
import type { ManualPriceFormPayload } from '@/modules/assets/prices/price-types';
import type { NonFungibleBalance } from '@/modules/balances/types/nfbalances';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

interface UseNftPriceManagementReturn {
  customPrice: Ref<ManualPriceFormPayload | null>;
  openPriceDialog: Ref<boolean>;
  deletePrice: (item: NonFungibleBalance) => Promise<void>;
  setPriceForm: (item: NonFungibleBalance) => void;
  showDeleteConfirmation: (item: NonFungibleBalance) => void;
}

export function useNftPriceManagement(
  fetchData: () => Promise<void>,
): UseNftPriceManagementReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { deleteLatestPrice } = useAssetPricesApi();
  const { show } = useConfirmStore();

  const openPriceDialog = ref<boolean>(false);
  const customPrice = ref<ManualPriceFormPayload | null>(null);

  async function deletePrice(toDeletePrice: NonFungibleBalance): Promise<void> {
    try {
      await deleteLatestPrice(toDeletePrice.id);
      await fetchData();
    }
    catch {
      notifyError(
        t('assets.custom_price.delete.error.title'),
        t('assets.custom_price.delete.error.message', {
          asset: toDeletePrice.name ?? toDeletePrice.id,
        }),
      );
    }
  }

  function setPriceForm(item: NonFungibleBalance): void {
    set(customPrice, {
      fromAsset: item.id,
      price: item.priceInAsset.toFixed(),
      toAsset: item.priceAsset,
    });
    set(openPriceDialog, true);
  }

  function showDeleteConfirmation(item: NonFungibleBalance): void {
    show(
      {
        message: t('assets.custom_price.delete.message', {
          asset: !item ? '' : item.name ?? item.id,
        }),
        title: t('assets.custom_price.delete.tooltip'),
      },
      async () => deletePrice(item),
    );
  }

  return {
    customPrice,
    deletePrice,
    openPriceDialog,
    setPriceForm,
    showDeleteConfirmation,
  };
}
