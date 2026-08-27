<script setup lang="ts">
import { startPromise } from '@shared/utils';
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

/**
 * Draws the WalletConnect pairing URI onto this dialog's own canvas.
 *
 * @remarks
 * `qrcode` is imported at draw time rather than at module scope, which keeps it out of the initial
 * bundle: nothing needs it until a pairing is actually started.
 */
async function drawPairingQr(): Promise<void> {
  const canvas = get(qrCanvas);
  const uri = get(connectUri);
  if (!canvas || !uri)
    return;

  try {
    const { toCanvas } = await import('qrcode');
    await toCanvas(canvas, uri, { width: 240 });
  }
  catch (error) {
    logger.error('Failed to render WalletConnect QR code', error);
  }
}

watch([qrCanvas, connectUri], () => {
  startPromise(drawPairingQr());
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
