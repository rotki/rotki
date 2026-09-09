<script setup lang="ts">
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { RPC_CONNECT_ERROR, summariseRpcConnectError } from '@/modules/settings/general/rpc/providers/rpc-connect-error';
import { RPC_SETUP_STATUS, type RpcSetupRow } from '@/modules/settings/general/rpc/providers/use-rpc-provider-setup';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const { row, message = '' } = defineProps<{
  /** The backend's own words, already masked, shown under a chain that was left out. */
  message?: string;
  row: RpcSetupRow;
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();

const kept = computed<boolean>(() =>
  row.status === RPC_SETUP_STATUS.ADDED || row.status === RPC_SETUP_STATUS.UPDATED);

/** Three words for why a chain was left out, with the backend's own message kept for the details. */
const reason = computed<string>(() => {
  if (row.status !== RPC_SETUP_STATUS.FAILED)
    return '';

  const kind = summariseRpcConnectError(row.error ?? '');
  if (kind === RPC_CONNECT_ERROR.REJECTED)
    return t('rpc_provider_setup.apply.reason.rejected');
  if (kind === RPC_CONNECT_ERROR.WRONG_NETWORK)
    return t('rpc_provider_setup.apply.reason.wrong_network');

  return kind === RPC_CONNECT_ERROR.UNREACHABLE
    ? t('rpc_provider_setup.apply.reason.unreachable')
    : t('rpc_provider_setup.apply.reason.unknown');
});
</script>

<template>
  <div
    class="flex items-center gap-2 py-2"
    data-testid="provider-result"
  >
    <ChainIcon
      :chain="row.chain"
      size="20px"
    />
    <div class="flex flex-col min-w-0">
      <span
        class="text-sm"
        :class="{ 'text-rui-text-secondary': row.status === RPC_SETUP_STATUS.PENDING }"
      >
        {{ getChainName(row.chain) }}
      </span>
      <span
        v-if="message"
        class="text-xs text-rui-text-secondary break-all"
      >
        {{ message }}
      </span>
    </div>

    <div class="ml-auto flex items-center gap-2 text-xs shrink-0">
      <template v-if="kept">
        <span
          v-if="row.archive"
          class="text-rui-text-secondary"
        >
          {{ t('rpc_provider_setup.apply.archive') }}
        </span>
        <RuiIcon
          name="lu-check"
          size="16"
          class="text-rui-success"
        />
      </template>
      <template v-else-if="row.status === RPC_SETUP_STATUS.FAILED">
        <span class="text-rui-text-secondary">{{ reason }}</span>
        <RuiIcon
          name="lu-x"
          size="16"
          class="text-rui-error"
        />
      </template>
      <RuiProgress
        v-else-if="row.status === RPC_SETUP_STATUS.RUNNING"
        circular
        variant="indeterminate"
        size="16"
        color="primary"
      />
      <RuiIcon
        v-else
        name="lu-minus"
        size="16"
        class="text-rui-text-disabled"
      />
    </div>
  </div>
</template>
