<script setup lang="ts">
import type { NftAsset } from '@/types/nfts';
import {
  getAddressFromEvmIdentifier,
  getAddressFromSolanaIdentifier,
  isEvmIdentifier,
  isSolanaTokenIdentifier,
} from '@rotki/common';
import { getNftAssetIdDetail, isEvmIdentifierWithNftId } from '@rotki/common/lib';
import { useAssetPageNavigation } from '@/composables/assets/navigation';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSpamAsset } from '@/composables/assets/spam';
import { useRefMap } from '@/composables/utils/useRefMap';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { EVM_TOKEN, SOLANA_CHAIN, SOLANA_TOKEN } from '@/types/asset';

const props = defineProps<{
  asset: NftAsset;
  hideActions: boolean;
  isCollectionParent: boolean;
  iconOnly: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { asset, isCollectionParent } = toRefs(props);

const symbol = useRefMap(asset, asset => asset.symbol ?? '');
const name = useRefMap(asset, asset => asset.name ?? '');
const identifier = useRefMap(asset, asset => asset.identifier);

const { navigateToDetails } = useAssetPageNavigation(identifier, isCollectionParent);

const [DefineNftDetails, ReuseNftDetails] = createReusableTemplate<{
  contractAddress: string;
  nftId: string;
}>();

type ConfirmType = 'ignore' | 'mark_as_spam';
const confirm = ref(false);
const confirmType = ref<ConfirmType>('ignore');

const { ignoreAsset, useIsAssetIgnored } = useIgnoredAssetsStore();
const isSpamAsset = computed<boolean>(() => get(asset).isSpam);
const isIgnoredAsset = useIsAssetIgnored(identifier);
const { markAssetsAsSpam } = useSpamAsset();
const { refetchAssetInfo } = useAssetInfoRetrieval();

const contractInfo = computed<{ address: string; location: string } | undefined>(() => {
  const id = get(identifier);
  const assetVal = get(asset);
  const type = assetVal.assetType;

  if (isEvmIdentifier(id) && type === EVM_TOKEN) {
    return {
      address: getAddressFromEvmIdentifier(id),
      location: assetVal?.evmChain ?? undefined,
    };
  }

  if (isSolanaTokenIdentifier(id) && type === SOLANA_TOKEN) {
    return {
      address: getAddressFromSolanaIdentifier(id),
      location: SOLANA_CHAIN,
    };
  }

  return undefined;
});

function actionClick(action: ConfirmType) {
  set(confirm, true);
  set(confirmType, action);
}

async function confirmAction() {
  const id = get(identifier);
  if (get(confirmType) === 'ignore') {
    await ignoreAsset(id);
  }
  else {
    await markAssetsAsSpam([id]);
  }

  refetchAssetInfo(id);
  emit('refresh');
  set(confirm, false);
}

function setConfirm(value: boolean) {
  set(confirm, value);
}

defineExpose({
  setConfirm,
});
</script>

<template>
  <div class="px-2 break-words">
    <div class="py-1 relative">
      <Transition
        enter-active-class="transition-all duration-100 ease-out"
        leave-active-class="transition-all duration-100 ease-in"
        enter-from-class="translate-y-5 opacity-0"
        enter-to-class="translate-y-0 opacity-100"
        leave-from-class="translate-y-0 opacity-100"
        leave-to-class="translate-y-[-20px] opacity-0"
        mode="out-in"
      >
        <div
          v-if="confirm"
          key="confirm"
          class="w-full flex items-center gap-2 justify-between text-rui-text-secondary pl-1 py-[1px]"
        >
          <div class="text-rui-warning text-xs leading-[1]">
            {{ confirmType === 'ignore'
              ? t('assets.action.confirm.ignore')
              : t('assets.action.confirm.mark_as_spam') }}
          </div>
          <div class="flex gap-1">
            <RuiButton
              variant="text"
              icon
              size="sm"
              color="error"
              @click="confirm = false"
            >
              <RuiIcon
                size="16"
                color="error"
                name="lu-x"
              />
            </RuiButton>
            <RuiButton
              variant="text"
              icon
              size="sm"
              @click="confirmAction()"
            >
              <RuiIcon
                size="16"
                color="success"
                name="lu-check"
              />
            </RuiButton>
          </div>
        </div>
        <div
          v-else
          key="actions"
          class="flex items-center gap-1"
        >
          <RuiButton
            variant="text"
            color="primary"
            size="sm"
            class="!py-0.5"
            @click="navigateToDetails()"
          >
            {{ t('assets.go_to_asset_detail') }}
            <template #append>
              <RuiIcon
                name="lu-arrow-up-right"
                size="18"
              />
            </template>
          </RuiButton>
          <template v-if="!hideActions">
            <div
              v-if="isIgnoredAsset || isSpamAsset"
              class="text-xs text-rui-info bg-rui-info-lighter/[0.1] px-1 py-1 rounded-md flex items-center gap-1"
            >
              <RuiIcon
                name="lu-info"
                size="16"
              />
              {{ isSpamAsset ? t('assets.action.info.mark_as_spam') : t('assets.action.info.ignore') }}
            </div>
            <template v-else>
              <RuiDivider
                vertical
                class="h-6"
              />
              <div class="w-full flex items-center gap-1">
                <RuiTooltip
                  :open-delay="200"
                  :popper="{ placement: 'top' }"
                >
                  <template #activator>
                    <RuiButton
                      variant="text"
                      color="error"
                      class="!py-0.5"
                      size="sm"
                      @click="actionClick('ignore')"
                    >
                      <template #append>
                        <RuiIcon
                          name="lu-eye-off"
                          size="18"
                        />
                      </template>
                    </RuiButton>
                  </template>
                  {{ t('assets.action.ignore') }}
                </RuiTooltip>
                <RuiTooltip
                  v-if="asset.assetType === EVM_TOKEN"
                  :open-delay="200"
                  :popper="{ placement: 'top' }"
                >
                  <template #activator>
                    <RuiButton
                      variant="text"
                      color="error"
                      class="!py-0.5"
                      size="sm"
                      @click="actionClick('mark_as_spam')"
                    >
                      <template #append>
                        <RuiIcon
                          name="lu-ban"
                          size="18"
                        />
                      </template>
                    </RuiButton>
                  </template>
                  {{ t('assets.action.mark_as_spam') }}
                </RuiTooltip>
              </div>
            </template>
          </template>
        </div>
      </Transition>
    </div>
    <div
      v-if="contractInfo"
      class="pt-2 pb-1 px-1 border-t border-default"
    >
      <div class="!text-[10px] !leading-[1] text-caption text-rui-text-secondary uppercase">
        {{ t('transactions.events.form.contract_address.label') }}
      </div>

      <HashLink
        :text="contractInfo.address"
        :location="contractInfo.location"
        type="token"
        class="text-[11px]"
        :truncate-length="9"
      />
    </div>
    <DefineNftDetails #default="{ contractAddress, nftId }">
      <div class="pt-2 pb-1 px-1 border-t border-default">
        <div class="!text-[10px] !leading-[1] text-caption text-rui-text-secondary uppercase">
          {{ t('transactions.events.form.contract_address.label') }}
        </div>
        <HashLink
          :text="contractAddress"
          :location="asset?.evmChain ?? undefined"
          type="token"
          class="text-[11px]"
          :truncate-length="9"
        />
      </div>
      <div class="pt-2 pb-1 px-1 border-t border-default">
        <div class="!text-[10px] !leading-[1] text-caption text-rui-text-secondary uppercase">
          {{ t('nft_balance_table.token_id') }}
        </div>

        <div class="text-xs py-1">
          #{{ nftId }}
        </div>
      </div>
    </DefineNftDetails>
    <ReuseNftDetails
      v-if="isEvmIdentifierWithNftId(asset.identifier)"
      v-bind="getNftAssetIdDetail(asset.identifier)!"
    />
    <div
      v-if="iconOnly"
      class="pt-2 pb-1 px-1 border-t border-default"
    >
      <div class="!text-[10px] !leading-[1] text-caption text-rui-text-secondary uppercase">
        {{ t('common.name') }}
      </div>

      <div class="text-xs py-0.5">
        {{ name }}
        <template v-if="name !== symbol">
          {{ t('assets.asset_symbol', { symbol }) }}
        </template>
      </div>
    </div>
  </div>
</template>
