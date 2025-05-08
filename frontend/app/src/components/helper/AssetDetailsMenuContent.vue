<script setup lang="ts">
import type { NftAsset } from '@/types/nfts';
import { useAssetPageNavigation } from '@/composables/assets/navigation';
import { useSpamAsset } from '@/composables/assets/spam';
import { useRefMap } from '@/composables/utils/useRefMap';
import CopyButton from '@/modules/common/links/CopyButton.vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { truncateAddress } from '@/utils/truncate';
import { getAddressFromEvmIdentifier, isEvmIdentifier } from '@rotki/common';

const props = defineProps<{
  asset: NftAsset;
  hideActions: boolean;
  isCollectionParent: boolean;
  iconOnly: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { asset, isCollectionParent } = toRefs(props);

const symbol = useRefMap(asset, asset => asset.symbol ?? '');
const name = useRefMap(asset, asset => asset.name ?? '');
const identifier = useRefMap(asset, asset => asset.identifier);

const { navigateToDetails } = useAssetPageNavigation(identifier, isCollectionParent);

type ConfirmType = 'ignore' | 'mark_as_spam';
const confirm = ref(false);
const confirmType = ref<ConfirmType>('ignore');

const { ignoreAsset, useIsAssetIgnored } = useIgnoredAssetsStore();
const isSpamAsset = computed(() => get(asset).protocol === 'spam');
const isIgnoredAsset = useIsAssetIgnored(identifier);
const { markAssetsAsSpam } = useSpamAsset();

function actionClick(action: ConfirmType) {
  set(confirm, true);
  set(confirmType, action);
}

async function confirmAction() {
  if (get(confirmType) === 'ignore') {
    await ignoreAsset(get(identifier));
  }
  else {
    await markAssetsAsSpam([get(identifier)]);
  }
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
    <div class="py-2 flex items-center gap-1 border-b border-default">
      <RuiButton
        variant="text"
        color="primary"
        size="sm"
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
          class="text-xs text-rui-info bg-rui-info-lighter/[0.1] px-2 py-1 rounded-md flex items-center gap-2"
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
          <div class="flex-1 flex relative">
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
                v-if="!confirm"
                key="actions"
                class="w-full flex items-center gap-2"
              >
                <RuiButton
                  variant="text"
                  color="error"
                  size="sm"
                  @click="actionClick('ignore')"
                >
                  {{ t('assets.action.ignore') }}
                  <template #append>
                    <RuiIcon
                      name="lu-eye-off"
                      size="18"
                    />
                  </template>
                </RuiButton>
                <RuiButton
                  variant="text"
                  color="error"
                  size="sm"
                  @click="actionClick('mark_as_spam')"
                >
                  {{ t('assets.action.mark_as_spam') }}
                  <template #append>
                    <RuiIcon
                      name="lu-ban"
                      size="18"
                    />
                  </template>
                </RuiButton>
              </div>
              <div
                v-else
                key="confirm"
                class="w-full flex items-center gap-2 justify-between text-rui-text-secondary"
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
            </Transition>
          </div>
        </template>
      </template>
    </div>
    <div class="py-2 px-1">
      <div class="!text-xs text-caption text-rui-text-secondary uppercase">
        {{ t('assets.asset_identifier') }}
      </div>
      <div class="flex items-center gap-2">
        <div class="text-[11px] font-mono">
          {{ truncateAddress(identifier, 24) }}
        </div>
        <CopyButton
          :text="asset.identifier"
          size="12"
        />
      </div>
    </div>
    <div
      v-if="isEvmIdentifier(asset.identifier)"
      class="pt-2 pb-1 px-1 border-t border-default"
    >
      <div class="!text-xs text-caption text-rui-text-secondary uppercase">
        {{ t('transactions.events.form.contract_address.label') }}
      </div>

      <HashLink
        :text="getAddressFromEvmIdentifier(asset.identifier)"
        :location="asset?.evmChain ?? undefined"
        type="token"
        class="text-[11px]"
        :truncate-length="0"
      />
    </div>
    <div
      v-if="iconOnly"
      class="py-2 px-1 border-t border-default"
    >
      <div class="!text-xs text-caption text-rui-text-secondary uppercase">
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
