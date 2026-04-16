<script setup lang="ts">
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import { useScramble } from '@/modules/settings/use-scramble';
import AppImage from '@/modules/shell/components/AppImage.vue';
import EnsAvatar from '@/modules/shell/components/display/EnsAvatar.vue';

const { counterparty, location, address } = defineProps<{
  counterparty?: string;
  location: string;
  address?: string;
}>();

defineSlots<{
  default: () => void;
}>();

const { getEventCounterpartyData } = useHistoryEventCounterpartyMappings();
const { getAddressName } = useAddressNameResolution();
const { getChain } = useSupportedChains();
const { scrambleAddress, scrambleData } = useScramble();

const { isDark } = useRotkiTheme();

const counterpartyData = getEventCounterpartyData(() => counterparty);

const useDarkModeImage = computed(() => get(isDark) && get(counterpartyData)?.darkmodeImage);

const counterpartyImageSrc = computed<string | undefined>(() => {
  const counterpartyVal = get(counterpartyData);

  if (!counterpartyVal)
    return undefined;

  if (get(useDarkModeImage)) {
    return getPublicProtocolImagePath(counterpartyVal.darkmodeImage!);
  }

  if (counterpartyVal.image) {
    return getPublicProtocolImagePath(counterpartyVal.image);
  }

  return undefined;
});

const addressAliasName = computed<string | undefined>(() => {
  if (!address || get(scrambleData)) {
    return undefined;
  }

  return getAddressName(address, getChain(location));
});

const displayAddress = computed<string | undefined>(() => {
  if (!address) {
    return undefined;
  }

  return scrambleAddress(address);
});
</script>

<template>
  <RuiBadge
    v-if="counterpartyData || displayAddress"
    class="[&_span]:!px-0"
    color="default"
    offset-x="-8"
    offset-y="6"
  >
    <template #icon>
      <RuiTooltip
        :popper="{ placement: 'top', scroll: false, resize: false }"
        :open-delay="400"
      >
        <template #activator>
          <div
            class="rounded-full overflow-hidden bg-rui-grey-100 border-2 border-white dark:border-black size-6 flex items-center justify-center"
            :class="{ '!bg-black': useDarkModeImage }"
          >
            <template v-if="counterpartyData">
              <RuiIcon
                v-if="counterpartyData.icon"
                :name="counterpartyData.icon"
                :color="counterpartyData.color"
              />

              <AppImage
                v-if="counterpartyImageSrc"
                :src="counterpartyImageSrc"
                contain
                size="20px"
              />
            </template>
            <EnsAvatar
              v-else-if="displayAddress"
              size="20px"
              :address="displayAddress"
              avatar
            />
          </div>
        </template>
        <div v-if="counterpartyData">
          {{ counterpartyData.label }}
        </div>
        <div
          v-else-if="displayAddress"
          class="text-center"
        >
          <div v-if="addressAliasName">
            {{ addressAliasName }}
          </div>
          {{ displayAddress }}
        </div>
      </RuiTooltip>
    </template>
    <slot />
  </RuiBadge>
  <div v-else>
    <slot />
  </div>
</template>
