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
  <VRow>
    <VCol cols="auto">
      <VTooltip open-delay="400" top>
        <template #activator="{ on, attrs }">
          <div v-bind="attrs" v-on="on">
            <VBtnToggle v-model="filterType" dense mandatory>
              <VBtn value="validator">{{ t('eth2_page.toggle.key') }}</VBtn>
              <VBtn value="address">
                {{ t('eth2_page.toggle.depositor') }}
              </VBtn>
            </VBtnToggle>
          </div>
        </template>
        <span>{{ t('eth2_page.toggle.hint') }}</span>
      </VTooltip>
    </VCol>
    <VCol>
      <VRow class="ml-8">
        <VCol>
          <Eth2ValidatorFilter
            :value="value"
            :filter-type="filterType"
            @input="emit('input', $event)"
          />
        </VCol>
        <VCol>
          <EthValidatorRangeFilter
            @update:period="emit('update:period', $event)"
          />
        </VCol>
      </VRow>
    </VCol>
  </VRow>
</template>
