<template>
  <div class="d-flex flex-row labeled-address-display align-center">
    <v-tooltip top open-delay="400" :disabled="!truncated && !ethName">
      <template #activator="{ on }">
        <span
          data-cy="labeled-address-display"
          class="labeled-address-display__address"
          :class="xsOnly ? 'labeled-address-display__address--mobile' : null"
          v-on="on"
        >
          <v-chip label outlined class="labeled-address-display__chip">
            <v-avatar size="24" class="mr-2">
              <v-img :src="makeBlockie(address)" />
            </v-avatar>
            <template v-if="!!label && !ethName">
              <span class="text-truncate">
                {{
                  t('labeled_address_display.label', {
                    label: label
                  })
                }}
              </span>
              <span v-if="displayAddress && !smAndDown" class="px-1">
                {{ t('labeled_address_display.divider') }}
              </span>
            </template>
            <span
              v-if="!smAndDown || !label"
              :class="{ 'blur-content': !shouldShowAmount }"
            >
              {{ displayAddress }}
            </span>
          </v-chip>
        </span>
      </template>
      <div>
        <span v-if="!!label"> {{ account.label }}</span>
        <span v-if="smAndDown && ethName"> ({{ ethName }})</span>
      </div>
      <div>{{ address }}</div>
    </v-tooltip>
    <div class="labeled-address-display__actions">
      <hash-link :text="account.address" buttons small :chain="account.chain" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import makeBlockie from 'ethereum-blockies-base64';
import { PropType } from 'vue';
import { useTheme } from '@/composables/common';
import { truncateAddress, truncationPoints } from '@/filters';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useSessionSettingsStore } from '@/store/settings/session';
import { randomHex } from '@/utils/data';

const { t } = useI18n();

const props = defineProps({
  account: { required: true, type: Object as PropType<GeneralAccount> }
});

const { account } = toRefs(props);
const { currentBreakpoint } = useTheme();
const { scrambleData, shouldShowAmount } = storeToRefs(
  useSessionSettingsStore()
);

const { ethNameSelector } = useEthNamesStore();
const ethName = computed<string | null>(() =>
  get(ethNameSelector(get(account).address))
);

const xsOnly = computed(() => get(currentBreakpoint).xsOnly);
const smAndDown = computed(() => get(currentBreakpoint).smAndDown);

const address = computed<string>(() => {
  return get(scrambleData) ? randomHex() : get(account).address;
});

const breakpoint = computed<string>(() => {
  return get(account).label.length > 0 && get(currentBreakpoint).mdAndDown
    ? 'sm'
    : get(currentBreakpoint).name;
});

const truncationLength = computed<number>(() => {
  let truncationPoint = truncationPoints[get(breakpoint)];
  if (truncationPoint && get(account).label) {
    return 4;
  }
  return truncationPoint ?? 4;
});

const truncatedAddress = computed(() => {
  return truncateAddress(get(address), get(truncationLength));
});

const displayAddress = computed<string>(() => {
  if (get(ethName)) return get(ethName) as string;
  if (get(truncatedAddress).length >= get(address).length) {
    return get(address);
  }
  return get(truncatedAddress);
});

const truncated = computed<boolean>(() => {
  if (get(truncatedAddress).length >= get(address).length) {
    return false;
  }
  return get(truncatedAddress).includes('...');
});

const label = computed<string>(() => {
  const bp = get(currentBreakpoint);
  const label = get(account).label;
  let length = -1;

  if (bp.xlOnly && label.length > 50) {
    length = 47;
  } else if (bp.lgOnly && label.length > 38) {
    length = 35;
  } else if (bp.md && label.length > 27) {
    length = 24;
  } else if (bp.smOnly && label.length > 19) {
    length = 16;
  }

  if (length > 0) {
    return label.substr(0, length) + '...';
  }

  return label;
});
</script>

<style scoped lang="scss">
.labeled-address-display {
  max-height: 30px;
  width: 100%;

  &__address {
    width: 100%;
    font-weight: 500;
    padding-top: 6px;
    padding-bottom: 6px;

    &--mobile {
      max-width: 120px;
    }

    :deep() {
      .v-chip {
        background-color: white !important;

        &--label {
          border-top-right-radius: 0 !important;
          border-bottom-right-radius: 0 !important;
        }
      }
    }
  }

  &__actions {
    height: 32px;
    background-color: var(--v-rotki-light-grey-base);
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-left-width: 0;
    border-radius: 0 4px 4px 0;
    display: inline-block;
  }

  &__chip {
    width: 100%;
  }
}

.blur-content {
  filter: blur(0.75em);
}
</style>
