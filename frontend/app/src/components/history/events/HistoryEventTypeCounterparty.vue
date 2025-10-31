<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import EnsAvatar from '@/components/display/EnsAvatar.vue';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { useSupportedChains } from '@/composables/info/chains';
import { useScramble } from '@/composables/scramble';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { getPublicProtocolImagePath } from '@/utils/file';

const props = defineProps<{
  counterparty?: string;
  location: string;
  address?: string;
}>();

const { address, counterparty, location } = toRefs(props);

const { getEventCounterpartyData } = useHistoryEventCounterpartyMappings();
const { addressNameSelector } = useAddressesNamesStore();
const { getChain } = useSupportedChains();
const { scrambleAddress, scrambleData } = useScramble();

const { isDark } = useRotkiTheme();

const counterpartyData = getEventCounterpartyData(counterparty);

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
  const addressVal = get(address);
  if (!addressVal || get(scrambleData)) {
    return undefined;
  }

  return get(addressNameSelector(addressVal, getChain(get(location))));
});

const displayAddress = computed<string | undefined>(() => {
  const addressVal = get(address);

  if (!addressVal) {
    return undefined;
  }

  return scrambleAddress(addressVal);
});
</script>

<template>
  <RuiBadge
    v-if="counterpartyData || displayAddress"
    class="[&_span]:!px-0"
    color="default"
    offset-x="-6"
    offset-y="6"
  >
    <template #icon>
      <RuiTooltip
        :popper="{ placement: 'top' }"
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
