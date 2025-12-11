<script setup lang="ts">
import WalletImportSelection from '@/components/accounts/blockchain/WalletImportSelection.vue';
import { useInterop } from '@/composables/electron-interop';
import { useMessageStore } from '@/store/message';

defineProps<{
  disabled: boolean;
}>();

const emit = defineEmits<{
  'update:addresses': [addresses: string[]];
}>();

const { t } = useI18n({ useScope: 'global' });

const [DefineButton, ReuseButton] = createReusableTemplate<{ buttonDisabled?: boolean; onClick?: () => void }>();
const { isPackaged, metamaskImport } = useInterop();
const { setMessage } = useMessageStore();

async function importAddresses() {
  try {
    const addresses = await metamaskImport();
    emit('update:addresses', addresses);
  }
  catch (error: any) {
    setMessage({
      description: error.message,
      success: false,
      title: t('input_mode_select.import_from_wallet.label'),
    });
  }
}
</script>

<template>
  <DefineButton #default="{ buttonDisabled, onClick }">
    <RuiTooltip :disabled="disabled">
      <template #activator>
        <RuiButton
          variant="outlined"
          color="primary"
          class="min-h-[3.5rem] relative"
          :class="{ 'opacity-50': buttonDisabled || disabled }"
          :disabled="buttonDisabled || disabled"
          @click="onClick?.()"
        >
          <RuiIcon name="lu-wallet-minimal" />
          <template #append>
            <div class="absolute w-4 h-4 bg-current rounded-full text-primary right-2 bottom-2 flex items-center justify-center">
              <RuiIcon
                name="lu-download"
                class="text-white"
                size="10"
              />
            </div>
          </template>
        </RuiButton>
      </template>
      {{ t('input_mode_select.import_from_wallet.label') }}
    </RuiTooltip>
  </DefineButton>

  <ReuseButton
    v-if="isPackaged"
    :on-click="importAddresses"
  />

  <WalletImportSelection
    v-else
    @import-addresses="emit('update:addresses', $event)"
  >
    <template #default="{ attrs }">
      <ReuseButton v-bind="attrs" />
    </template>
  </WalletImportSelection>
</template>
