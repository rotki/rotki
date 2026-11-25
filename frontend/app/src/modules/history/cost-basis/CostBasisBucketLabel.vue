<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

const { location, locationLabel, method, protocol } = defineProps<{
  location: string;
  locationLabel: string | null;
  method: string;
  protocol: string | null;
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChainName, matchChain } = useSupportedChains();

/** The protocol holding the asset, or the wallet itself on a chain. An exchange has neither. */
const holder = computed<string | undefined>(() => {
  if (protocol)
    return protocol;
  return matchChain(location) ? t('accounting_overlay.wallet') : undefined;
});

/** The full name of the cost basis method, as the settings name it. */
const methodName = computed<string>(() => {
  switch (method) {
    case 'acb':
      return t('account_settings.cost_basis_method_settings.labels.acb');
    case 'fifo':
      return t('account_settings.cost_basis_method_settings.labels.fifo');
    case 'hifo':
      return t('account_settings.cost_basis_method_settings.labels.hifo');
    case 'lifo':
      return t('account_settings.cost_basis_method_settings.labels.lifo');
    default:
      return method;
  }
});
</script>

<template>
  <div class="flex items-center gap-3">
    <div class="flex items-center gap-2 min-w-0 flex-1">
      <LocationIcon
        :item="location"
        icon
        size="20px"
        class="shrink-0"
      />
      <div class="flex flex-col min-w-0 leading-tight">
        <span class="text-sm font-medium truncate">{{ getChainName(location) }}</span>
        <span
          v-if="holder || locationLabel"
          class="text-xs text-rui-text-secondary truncate"
          data-testid="cost-basis-bucket-holder"
        >
          {{ [holder, locationLabel].filter(Boolean).join(' · ') }}
        </span>
      </div>
    </div>
    <RuiTooltip
      :open-delay="300"
      :options="{ placement: 'top' }"
    >
      <template #activator>
        <span
          class="shrink-0 rounded px-1.5 py-0.5 text-[0.625rem] font-semibold uppercase tracking-wider bg-rui-grey-100 dark:bg-rui-grey-800 text-rui-text-secondary"
          data-testid="cost-basis-method"
        >
          {{ method }}
        </span>
      </template>
      {{ methodName }}
    </RuiTooltip>
  </div>
</template>
