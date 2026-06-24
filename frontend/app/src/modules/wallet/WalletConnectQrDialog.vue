<script setup lang="ts">
import { useClipboard } from '@vueuse/core';
import { logger } from '@/modules/core/common/logging/logging';
import { useWalletConnect } from '@/modules/wallet/use-wallet-connect';

const { t } = useI18n({ useScope: 'global' });

const { cancelConnect, connectUri, showConnectModal } = useWalletConnect();

const qrCanvas = useTemplateRef<HTMLCanvasElement>('qrCanvas');

const { copied, copy } = useClipboard({ source: () => get(connectUri) ?? '' });

const open = computed<boolean>({
  get: () => get(showConnectModal),
  set: (value) => {
    if (!value)
      cancelConnect();
  },
});

// Render the WalletConnect pairing URI to our own QR canvas via the lazily
// imported `qrcode` library (kept out of the main bundle).
watch([qrCanvas, connectUri], async ([canvas, uri]) => {
  if (!canvas || !uri)
    return;

  try {
    const { toCanvas } = await import('qrcode');
    await toCanvas(canvas, uri, { width: 240 });
  }
  catch (error) {
    logger.error('Failed to render WalletConnect QR code', error);
  }
});
</script>

<template>
  <RuiDialog
    v-model="open"
    max-width="400"
  >
    <RuiCard>
      <template #header>
        {{ t('wallet_connect_qr.title') }}
      </template>
      <template #subheader>
        {{ t('wallet_connect_qr.scan') }}
      </template>

      <div class="flex flex-col items-center gap-6 py-4">
        <div class="rounded-lg p-4 bg-white border border-rui-grey-300 shadow-sm">
          <canvas
            ref="qrCanvas"
            class="block"
          />
        </div>
        <RuiButton
          variant="text"
          color="primary"
          @click="copy()"
        >
          <template #prepend>
            <RuiIcon
              :name="copied ? 'lu-check' : 'lu-copy'"
              size="18"
            />
          </template>
          {{ copied ? t('wallet_connect_qr.copied') : t('wallet_connect_qr.copy') }}
        </RuiButton>
      </div>

      <template #footer>
        <div class="w-full flex justify-end">
          <RuiButton
            variant="outlined"
            @click="cancelConnect()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
