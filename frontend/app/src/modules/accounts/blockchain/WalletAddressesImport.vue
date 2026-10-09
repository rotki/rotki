<script setup lang="ts">
import WalletImportSelection from '@/modules/accounts/blockchain/WalletImportSelection.vue';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

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
  catch (error: unknown) {
    setMessage({
      description: getErrorMessage(error),
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
        <!-- level with the field box: the label above it takes the first 24px -->
        <RuiButton
          variant="outlined"
          color="primary"
          class="mt-6 size-9 px-0 relative"
          :class="{ 'opacity-50': buttonDisabled || disabled }"
          :disabled="buttonDisabled || disabled"
          @click="onClick?.()"
        >
          <RuiIcon
            name="lu-wallet-minimal"
            size="18"
          />
          <template #append>
            <div class="absolute size-3.5 bg-current rounded-full text-rui-primary right-0.5 bottom-0.5 flex items-center justify-center">
              <RuiIcon
                name="lu-download"
                class="text-white"
                size="9"
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
