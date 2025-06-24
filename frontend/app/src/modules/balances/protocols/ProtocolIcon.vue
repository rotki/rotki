<script lang="ts" setup>
import AppImage from '@/components/common/AppImage.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { useLocations } from '@/composables/locations';
import { useSessionSettingsStore } from '@/store/settings/session';
import { type ProtocolBalance, toSentenceCase } from '@rotki/common';

type LocationImage = { image: string; type: 'image' } | { icon: string; type: 'icon' } | undefined;

const props = defineProps<{
  protocolBalance: ProtocolBalance;
  asset?: string;
  loading?: boolean;
}>();

const { shouldShowAmount } = storeToRefs(useSessionSettingsStore());
const { locationData } = useLocations();
const { t } = useI18n({ useScope: 'global' });

const protocolName = computed<string>(() => {
  const data = get(locationData(props.protocolBalance.protocol));
  return data?.name || toSentenceCase(props.protocolBalance.protocol);
});

const location = computed<LocationImage>(() => {
  const protocol = props.protocolBalance.protocol;
  if (protocol === 'address') {
    return {
      icon: 'lu-wallet',
      type: 'icon',
    };
  }
  const data = get(locationData(protocol));

  if (!data) {
    return undefined;
  }

  if (data.image) {
    return {
      image: data.image,
      type: 'image',
    };
  }
  else if (data.icon) {
    return {
      icon: data.icon,
      type: 'icon',
    };
  }
  return undefined;
});
</script>

<template>
  <RuiTooltip
    :disabled="!shouldShowAmount"
    :close-delay="0"
    tooltip-class="!-ml-1"
  >
    <template #activator>
      <div
        data-cy="top-protocol"
        class="rounded-full size-8 flex items-center justify-center border bg-white border-rui-grey-300 dark:border-rui-grey-700 cursor-pointer"
      >
        <RuiIcon
          v-if="location?.type === 'icon'"
          color="secondary"
          :size="20"
          :name="location.icon"
        />
        <AppImage
          v-else-if="location?.type === 'image'"
          class="icon-bg rounded-full overflow-hidden"
          :src="location.image"
          size="24px"
          :loading="loading"
          contain
        />
        <RuiIcon
          v-else
          name="lu-blocks"
          color="secondary"
          :size="20"
        />
      </div>
    </template>

    <div class="flex flex-col gap-1">
      <div class="font-medium text-sm">
        {{ protocolName }}
        <div
          v-if="protocolBalance.containsManual"
          class="font-normal text-caption"
        >
          {{ t('protocol_icon.contains_manual') }}
        </div>
      </div>
      <AmountDisplay
        :value="protocolBalance.amount"
        :asset="asset"
        :asset-padding="0.1"
        data-cy="top-protocol-amount"
      />
      <AmountDisplay
        :asset-padding="0.1"
        fiat-currency="USD"
        :value="protocolBalance.usdValue"
        show-currency="symbol"
        data-cy="top-protocol-value"
      />
    </div>
  </RuiTooltip>
</template>
