<script setup lang="ts">
import { XpubAddressType, type XpubGroupWithBalance } from '@/modules/accounts/blockchain-accounts';

const { group } = defineProps<{
  group: XpubGroupWithBalance;
}>();

const { t } = useI18n({ useScope: 'global' });

const typeLabel = computed<string | undefined>(() => {
  switch (group.addressType) {
    case XpubAddressType.LEGACY:
      return t('account_form.xpub_detected.legacy');
    case XpubAddressType.NATIVE_SEGWIT:
      return t('account_form.xpub_detected.native_segwit');
    case XpubAddressType.SEGWIT:
      return t('account_form.xpub_detected.segwit');
    case XpubAddressType.TAPROOT:
      return t('account_form.xpub_detected.taproot');
    default:
      return undefined;
  }
});
</script>

<template>
  <div
    v-if="typeLabel || group.addressCount > 0"
    class="flex flex-wrap items-center gap-2 -mt-1 mb-2 pl-8"
    data-testid="xpub-row-summary"
  >
    <RuiChip
      v-if="typeLabel"
      tile
      size="sm"
      class="font-medium text-caption"
      data-testid="xpub-address-type"
    >
      {{ typeLabel }}
    </RuiChip>
    <span
      v-if="group.addressCount > 0"
      class="text-caption text-rui-text-secondary"
      data-testid="xpub-funded-count"
    >
      {{ t('account_balances.xpub.funded', { count: group.addressCount, funded: group.fundedAddressCount }, group.addressCount) }}
    </span>
  </div>
</template>
