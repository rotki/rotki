<script setup lang="ts">
import type { NftAsset } from '@/modules/assets/nfts';
import { isSpammableAssetType } from '@/modules/assets/types';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useAssetPageNavigation } from '@/modules/assets/use-asset-page-navigation';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';
import { injectEventPriceUpdate } from '@/modules/history/events/prices/use-event-price-update-trigger';
import HashLink from '@/modules/shell/components/HashLink.vue';

type ConfirmType = 'ignore' | 'mark_as_spam' | 'unignore' | 'unmark_spam';

const { asset, hideActions, isCollectionParent, iconOnly, timestamp } = defineProps<{
  asset: NftAsset;
  hideActions?: boolean;
  isCollectionParent?: boolean;
  iconOnly: boolean;
  timestamp?: number;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const confirm = ref<boolean>(false);
const confirmType = ref<ConfirmType>('ignore');

const { navigateToDetails } = useAssetPageNavigation(() => asset.identifier, () => isCollectionParent);
const { ignoreAsset, unignoreAsset } = useIgnoredAssetOperations();
const { useIsAssetIgnored } = useAssetsStore();
const { markAssetsAsSpam, removeAssetFromSpamList } = useSpamAsset();

const isIgnoredAsset = useIsAssetIgnored(() => asset.identifier);
const { refetchAssetInfo, useAssetContractInfo } = useAssetInfoRetrieval();

const contractInfo = useAssetContractInfo(() => asset.identifier);

const priceUpdateTrigger = injectEventPriceUpdate();
const canUpdatePrice = computed<boolean>(() => timestamp !== undefined && priceUpdateTrigger !== null);

function openPriceUpdate(): void {
  if (timestamp === undefined || !priceUpdateTrigger)
    return;
  priceUpdateTrigger.open({ asset: asset.identifier, timestamp });
}

function actionClick(action: ConfirmType): void {
  set(confirm, true);
  set(confirmType, action);
}

function confirmMessage(): string {
  const type = get(confirmType);
  if (type === 'ignore')
    return t('assets.action.confirm.ignore');
  else if (type === 'mark_as_spam')
    return t('assets.action.confirm.mark_as_spam');
  else if (type === 'unignore')
    return t('assets.action.confirm.unignore');
  else
    return t('assets.action.confirm.unmark_as_spam');
}

async function confirmAction(): Promise<void> {
  const id = asset.identifier;
  const type = get(confirmType);

  if (type === 'ignore') {
    await ignoreAsset(id);
  }
  else if (type === 'mark_as_spam') {
    await markAssetsAsSpam([id]);
  }
  else if (type === 'unignore') {
    await unignoreAsset(id);
  }
  else {
    await removeAssetFromSpamList(id);
  }

  refetchAssetInfo(id);
  emit('refresh');
  set(confirm, false);
}

function setConfirm(value: boolean): void {
  set(confirm, value);
}

defineExpose({
  setConfirm,
});
</script>

<template>
  <div class="flex flex-col py-1 break-words">
    <div
      v-if="confirm"
      class="flex flex-col gap-3 px-3 py-2"
      data-testid="asset-menu-confirm"
    >
      <span class="text-sm text-rui-text">
        {{ confirmMessage() }}
      </span>
      <div class="flex justify-end gap-2">
        <RuiButton
          variant="text"
          size="sm"
          @click="confirm = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          size="sm"
          data-testid="asset-menu-confirm-action"
          @click="confirmAction()"
        >
          {{ t('common.actions.confirm') }}
        </RuiButton>
      </div>
    </div>
    <div
      v-else
      class="flex flex-col text-rui-text-secondary"
    >
      <RuiButton
        variant="list"
        size="sm"
        data-testid="asset-menu-details"
        @click="navigateToDetails()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-arrow-right"
            size="16"
          />
        </template>
        {{ t('assets.go_to_asset_detail') }}
      </RuiButton>
      <RuiButton
        v-if="canUpdatePrice"
        variant="list"
        size="sm"
        data-testid="asset-update-price"
        @click="openPriceUpdate()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-dollar-sign"
            size="16"
          />
        </template>
        {{ t('assets.action.update_price') }}
      </RuiButton>
      <template v-if="!hideActions">
        <RuiButton
          v-if="asset.isSpam"
          variant="list"
          size="sm"
          @click="actionClick('unmark_spam')"
        >
          <template #prepend>
            <RuiIcon
              name="lu-shield-off"
              size="16"
            />
          </template>
          {{ t('assets.action.unmark_as_spam') }}
        </RuiButton>
        <RuiButton
          v-else-if="isIgnoredAsset"
          variant="list"
          size="sm"
          @click="actionClick('unignore')"
        >
          <template #prepend>
            <RuiIcon
              name="lu-eye"
              size="16"
            />
          </template>
          {{ t('assets.action.unignore') }}
        </RuiButton>
        <template v-else>
          <RuiButton
            variant="list"
            size="sm"
            @click="actionClick('ignore')"
          >
            <template #prepend>
              <RuiIcon
                name="lu-eye-off"
                size="16"
              />
            </template>
            {{ t('assets.action.ignore') }}
          </RuiButton>
          <RuiButton
            v-if="isSpammableAssetType(asset.assetType)"
            variant="list"
            size="sm"
            @click="actionClick('mark_as_spam')"
          >
            <template #prepend>
              <RuiIcon
                name="lu-ban"
                size="16"
              />
            </template>
            {{ t('assets.action.mark_as_spam') }}
          </RuiButton>
        </template>
      </template>
    </div>

    <div
      v-if="contractInfo"
      class="flex flex-col gap-0.5 px-3 pt-2 pb-1 mt-1 border-t border-rui-divider"
    >
      <span class="text-xs text-rui-text-secondary">
        {{ t('transactions.events.form.contract_address.label') }}
      </span>
      <HashLink
        :text="contractInfo.address"
        :location="contractInfo.location"
        type="token"
        class="text-xs"
        :truncate-length="6"
      />
    </div>

    <div
      v-if="contractInfo?.nftId"
      class="flex flex-col gap-0.5 px-3 pt-2 pb-1 mt-1 border-t border-rui-divider"
    >
      <span class="text-xs text-rui-text-secondary">
        {{ t('nft_balance_table.token_id') }}
      </span>
      <span class="text-xs">
        #{{ contractInfo.nftId }}
      </span>
    </div>

    <div
      v-if="iconOnly"
      class="flex flex-col gap-0.5 px-3 pt-2 pb-1 mt-1 border-t border-rui-divider"
    >
      <span class="text-xs text-rui-text-secondary">
        {{ t('common.name') }}
      </span>
      <span class="text-sm">
        {{ asset.name }}
        <template v-if="asset.name !== asset.symbol">
          {{ t('assets.asset_symbol', { symbol: asset.symbol }) }}
        </template>
      </span>
    </div>
  </div>
</template>
