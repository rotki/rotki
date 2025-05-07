<script setup lang="ts">
import type { Eth2ValidatorEntry } from '@rotki/common';
import { useScramble } from '@/composables/scramble';
import { truncateAddress } from '@/utils/truncate';

const props = withDefaults(
  defineProps<{
    validator: Eth2ValidatorEntry;
    horizontal?: boolean;
  }>(),
  {
    horizontal: false,
  },
);

const { horizontal } = toRefs(props);
const length = computed(() => (get(horizontal) ? 4 : 10));

const { t } = useI18n({ useScope: 'global' });

const { scrambleAddress, scrambleIdentifier, shouldShowAmount } = useScramble();
</script>

<template>
  <div
    :class="{
      flex: horizontal,
      blur: !shouldShowAmount,
    }"
  >
    <div class="font-medium text-truncate text-rui-text">
      {{ truncateAddress(scrambleAddress(validator.publicKey), length) }}
    </div>
    <div>
      <span
        v-if="horizontal"
        class="px-1"
      >
        -
      </span>
      <span
        v-else
        class="text-caption"
      >
        {{ t('common.validator_index') }}:
      </span>
      {{ scrambleIdentifier(validator.index) }}
    </div>
  </div>
</template>
