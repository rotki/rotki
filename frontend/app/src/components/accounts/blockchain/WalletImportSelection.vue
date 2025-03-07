<script setup lang="ts">
import { getAddressesFromWallet, getAllBrowserWalletProviders } from '@/utils/metamask';
import { useClearableMessages } from '@/composables/settings';
import type { EIP1193Provider, EIP6963ProviderDetail } from '@/types';

const emit = defineEmits<{
  'import-addresses': [addresses: string[]];
}>();

defineSlots<{
  default: (props: {
    attrs: {
      onMouseover: () => void;
      onMouseleave: () => void;
      onClick: () => void;
    } | {
      onMouseover?: undefined;
      onMouseleave?: undefined;
      onClick?: undefined;
    };
  }) => any;
}>();

const { t } = useI18n();

const loading = ref<boolean>(true);
const providers = ref<EIP6963ProviderDetail[]>([]);

const { clearAll, error, setError, setSuccess, stop, success } = useClearableMessages();

async function importAddressesWithProvider(provider: EIP1193Provider) {
  stop();
  clearAll();
  try {
    const addresses = await getAddressesFromWallet(provider);
    emit('import-addresses', addresses);
    setSuccess(t('input_mode_select.import_from_wallet.imported'));
  }
  catch (error: any) {
    setError(error.message);
  }
}

onBeforeMount(async () => {
  set(loading, true);
  set(providers, await getAllBrowserWalletProviders());
  set(loading, false);
});
</script>

<template>
  <RuiMenu
    menu-class="max-w-[16rem] w-[16rem] [&>div]:p-4"
    :popper="{ placement: 'right-end' }"
  >
    <template #activator="{ attrs }">
      <slot v-bind="{ attrs }" />
    </template>

    <RuiAlert
      v-if="success || error"
      class="mb-4"
      :type="success ? 'success' : 'error'"
    >
      {{ success || error }}
    </RuiAlert>

    <div
      v-if="loading"
      class="grid grid-cols-2 gap-2"
    >
      <RuiSkeletonLoader
        v-for="i in 4"
        :key="i"
        class="w-[113px] h-[84px]"
      />
    </div>
    <div v-else-if="providers.length > 0">
      <div class="grid grid-cols-2 gap-2">
        <RuiButton
          v-for="provider in providers"
          :key="provider.info.uuid"
          variant="outlined"
          color="primary"
          class="flex-col text-center text-rui-text-secondary text-sm py-3"
          @click="importAddressesWithProvider(provider.provider)"
        >
          <img
            :src="provider.info.icon"
            :alt="provider.info.name"
            class="w-8 h-8 mx-auto mb-2"
          />
          {{ provider.info.name }}
        </RuiButton>
      </div>
      <div class="pt-3 text-xs text-rui-text-secondary">
        {{ t('input_mode_select.import_from_wallet.only_metamask') }}
      </div>
    </div>
    <template v-else>
      <div class="font-bold mb-2">
        {{ t('input_mode_select.import_from_wallet.missing') }}
        {{ t('input_mode_select.import_from_wallet.missing_tooltip.title') }}
      </div>
      <ol class="list-disc pl-3">
        <li>
          {{ t('input_mode_select.import_from_wallet.missing_tooltip.wallet_is_not_installed') }}
        </li>
        <li>
          {{ t('input_mode_select.import_from_wallet.missing_tooltip.wallet_is_not_enabled') }}
        </li>
      </ol>
    </template>
  </RuiMenu>
</template>
