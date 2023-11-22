<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';

const props = defineProps<{
  account: GeneralAccount;
}>();

const { account } = toRefs(props);
const { scrambleData, shouldShowAmount, scrambleHex, scrambleIdentifier } =
  useScramble();
const { addressNameSelector, ensNameSelector } = useAddressesNamesStore();
const css = useCssModule();

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
  <RuiChip
    variant="outlined"
    :class="css['labeled-address-display']"
    size="sm"
    color="primary"
  >
    <RuiTooltip
      :popper="{ placement: 'top' }"
      open-delay="400"
      :disabled="!truncated && !aliasName"
    >
      <template #activator>
        <span
          data-cy="labeled-address-display"
          :class="[
            css['labeled-address-display__address'],
            { 'labeled-address-display__address--mobile': xs }
          ]"
        >
          <EnsAvatar :address="address" avatar />
          <span v-if="aliasName" class="text-truncate">
            {{ truncatedAliasName }}
          </span>
          <span v-else :class="{ 'blur-content': !shouldShowAmount }">
            {{ truncatedAddress }}
          </span>
        </span>
      </template>
      <div>
        <div v-if="aliasName">{{ aliasName }}</div>
        <div v-if="ensName && aliasName !== ensName">({{ ensName }})</div>
        <div>{{ address }}</div>
      </div>
    </RuiTooltip>
    <RuiDivider vertical :class="css['labeled-address-display__divider']" />
    <div :class="css['labeled-address-display__actions']">
      <HashLink
        class="h-full"
        :text="account.address"
        buttons
        size="14"
        :show-icon="false"
        :chain="account.chain"
      />
    </div>
  </RuiChip>
</template>

<style module lang="scss">
.labeled-address-display {
  background-color: var(--v-rotki-light-grey-base) !important;

  > span {
    @apply w-full flex items-center px-0;
  }

  &__address {
    &--mobile {
      @apply max-w-[9.375rem];
    }

    @apply flex items-center gap-2 text-rui-text-secondary;
  }

  &__divider {
    @apply h-[1.75rem] ml-auto px-0.5 border-black/[.12] dark:border-white/[.12];
  }

  &__actions {
    @apply flex items-center h-[1.75rem];
  }

  @apply w-full hover:cursor-default;
}

.blur-content {
  filter: blur(0.75em);
}
</style>
