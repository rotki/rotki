<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import EnsAvatar from '@/components/display/EnsAvatar.vue';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { useSupportedChains } from '@/composables/info/chains';
import { useScramble } from '@/composables/scramble';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { getPublicProtocolImagePath } from '@/utils/file';

const props = defineProps<{
  event: { counterparty: string | null; address?: string; location: string };
}>();

const { event } = toRefs(props);

const { getEventCounterpartyData } = useHistoryEventCounterpartyMappings();
const { addressNameSelector } = useAddressesNamesStore();
const { getChain } = useSupportedChains();
const { scrambleAddress, scrambleData } = useScramble();

const { isDark } = useRotkiTheme();

const counterparty = getEventCounterpartyData(event);

const useDarkModeImage = computed(() => get(isDark) && get(counterparty)?.darkmodeImage);

const counterpartyImageSrc = computed<string | undefined>(() => {
  const counterpartyVal = get(counterparty);

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

const addressAliasName = computed(() => {
  const eventVal = get(event);
  const address = eventVal.address;
  if (!address || get(scrambleData)) {
    return undefined;
  }

  return get(addressNameSelector(address, getChain(eventVal.location)));
});

const displayAddress = computed(() => {
  const address = get(event).address;

  if (!address) {
    return undefined;
  }

  return scrambleAddress(address);
});
</script>

<template>
  <RuiBadge
    v-if="counterparty || displayAddress"
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
            <template v-if="counterparty">
              <RuiIcon
                v-if="counterparty.icon"
                :name="counterparty.icon"
                :color="counterparty.color"
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
        <div v-if="counterparty">
          {{ counterparty.label }}
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
