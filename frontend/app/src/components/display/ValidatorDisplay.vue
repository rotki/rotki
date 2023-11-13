<script setup lang="ts">
import { type Eth2ValidatorEntry } from '@rotki/common/lib/staking/eth2';
import { truncateAddress } from '@/utils/truncate';

const props = withDefaults(
  defineProps<{
    validator: Eth2ValidatorEntry;
    horizontal?: boolean;
  }>(),
  {
    horizontal: false
  }
);

const { horizontal } = toRefs(props);
const length = computed(() => (get(horizontal) ? 4 : 10));

const { t } = useI18n();

const { scrambleIdentifier, scrambleHex, shouldShowAmount } = useScramble();

const css = useCssModule();
</script>

<template>
  <div
    class="p-2"
    :class="{
      flex: horizontal,
      [css.blur]: !shouldShowAmount
    }"
  >
    <div class="font-medium text-truncate">
      {{ truncateAddress(scrambleHex(validator.publicKey), length) }}
    </div>
    <div>
      <span v-if="horizontal" class="px-1"> - </span>
      <span v-else class="text-caption">
        {{ t('common.validator_index') }}:
      </span>
      {{ scrambleIdentifier(validator.validatorIndex) }}
    </div>
  </div>
</template>

<style module lang="scss">
.blur {
  filter: blur(0.75em);
}
</style>
