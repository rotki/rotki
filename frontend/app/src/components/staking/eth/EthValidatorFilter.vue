<script setup lang="ts">
import {
  type Eth2StakingFilter,
  type Eth2StakingFilterType,
  type EthStakingPeriod
} from '@rotki/common/lib/staking/eth2';

defineProps<{
  value: Eth2StakingFilter;
}>();

const emit = defineEmits<{
  (e: 'input', value: Eth2StakingFilter): void;
  (e: 'update:period', value: EthStakingPeriod): void;
}>();

const filterType: Ref<Eth2StakingFilterType> = ref('validator');

watch(filterType, () => emit('input', { accounts: [], validators: [] }));

const { t } = useI18n();
</script>

<template>
  <div class="flex flex-col md:flex-row md:items-center gap-4 md:gap-12">
    <RuiTooltip
      :popper="{ placement: 'top' }"
      open-delay="400"
      tooltip-class="max-w-[12rem]"
    >
      <template #activator>
        <RuiButtonGroup
          v-model="filterType"
          required
          variant="outlined"
          color="primary"
        >
          <template #default>
            <RuiButton value="validator" class="!py-2">
              {{ t('eth2_page.toggle.key') }}
            </RuiButton>
            <RuiButton value="address" class="!py-2">
              {{ t('eth2_page.toggle.depositor') }}
            </RuiButton>
          </template>
        </RuiButtonGroup>
      </template>
      <span>{{ t('eth2_page.toggle.hint') }}</span>
    </RuiTooltip>
    <div class="grid sm:grid-cols-2 flex-1 gap-4">
      <Eth2ValidatorFilter
        :value="value"
        :filter-type="filterType"
        @input="emit('input', $event)"
      />
      <EthValidatorRangeFilter @update:period="emit('update:period', $event)" />
    </div>
  </div>
</template>
