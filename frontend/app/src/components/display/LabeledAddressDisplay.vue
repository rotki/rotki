<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';

const props = defineProps<{
  account: GeneralAccount;
}>();

const { account } = toRefs(props);
const { scrambleData, shouldShowAmount, scrambleHex, scrambleIdentifier } =
  useScramble();
const { addressNameSelector, ensNameSelector } = useAddressesNamesStore();

const aliasName: ComputedRef<string> = computed(() => {
  if (get(scrambleData)) {
    return '';
  }

  const { address, chain } = get(account);
  const name = get(addressNameSelector(address, chain));

  if (!name) {
    return get(label);
  }

  return name;
});

const ensName: ComputedRef<string | null> = computed(() => {
  if (get(scrambleData)) {
    return null;
  }

  const { address } = get(account);
  return get(ensNameSelector(address));
});

const { xs, name } = useDisplay();

const address = computed<string>(() => {
  const address = get(account).address;
  return scrambleHex(address);
});

const truncationLength = computed<number>(() => {
  let truncationPoint = truncationPoints[get(name)];
  truncationPoint = truncationPoint ?? 4;

  return Math.max(4, truncationPoint);
});

const truncatedAddress: ComputedRef<string> = computed(() =>
  truncateAddress(get(address), get(truncationLength))
);

const truncated = computed<boolean>(() => {
  const truncated = get(truncatedAddress);
  if (truncated.length >= get(address).length) {
    return false;
  }
  return truncated.includes('...');
});

const label = computed<string>(() => {
  const label = get(account).label;

  if (consistOfNumbers(label)) {
    return scrambleIdentifier(label);
  }

  return label;
});

const truncatedAliasName: ComputedRef<string> = computed(() => {
  const name = get(aliasName);
  if (!name) {
    return '';
  }

  const length = get(truncationLength) * 2;

  if (length > 0 && name.length > length) {
    return `${name.slice(0, Math.max(0, length))}...`;
  }

  return name;
});
</script>

<template>
  <div class="d-flex flex-row labeled-address-display align-center">
    <VTooltip top open-delay="400" :disabled="!truncated && !aliasName">
      <template #activator="{ on }">
        <span
          data-cy="labeled-address-display"
          class="labeled-address-display__address"
          :class="xs ? 'labeled-address-display__address--mobile' : null"
          v-on="on"
        >
          <VChip label outlined class="labeled-address-display__chip">
            <VAvatar size="24" class="mr-2">
              <EnsAvatar :address="address" />
            </VAvatar>
            <span v-if="aliasName" class="text-truncate">
              {{ truncatedAliasName }}
            </span>
            <span v-else :class="{ 'blur-content': !shouldShowAmount }">
              {{ truncatedAddress }}
            </span>
          </VChip>
        </span>
      </template>
      <div>
        <div v-if="aliasName">{{ aliasName }}</div>
        <div v-if="ensName && aliasName !== ensName">({{ ensName }})</div>
        <div>{{ address }}</div>
      </div>
    </VTooltip>
    <div class="labeled-address-display__actions">
      <HashLink
        :text="account.address"
        buttons
        small
        :show-icon="false"
        :chain="account.chain"
      />
    </div>
  </div>
</template>

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
      max-width: 150px;
    }

    /* stylelint-disable selector-class-pattern,selector-nested-pattern */

    :deep(.v-chip--label) {
      border-top-right-radius: 0 !important;
      border-bottom-right-radius: 0 !important;
    }

    /* stylelint-enable selector-class-pattern,selector-nested-pattern */
  }

  &__actions {
    height: 32px;
    background-color: var(--v-rotki-light-grey-base);
    border: 1px solid var(--border-color);
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
