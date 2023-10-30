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
</script>

<template>
  <div
    :class="{
      [$style.wrapper]: true,
      [$style.horizontal]: horizontal
    }"
  >
    <div class="font-medium text-truncate">
      {{ truncateAddress(validator.publicKey, length) }}
    </div>
    <div>
      <span v-if="horizontal" :class="$style.divider"> - </span>
      <span v-else class="text-caption">
        {{ t('common.validator_index') }}:
      </span>
      {{ validator.validatorIndex }}
    </div>
  </div>
</template>

<style lang="scss" module>
.wrapper {
  padding: 8px;
}

.divider {
  padding-left: 4px;
  padding-right: 4px;
}

.horizontal {
  display: flex;
  flex-direction: row;
}
</style>
