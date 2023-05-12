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
  <v-row>
    <v-col cols="auto">
      <v-tooltip open-delay="400" top>
        <template #activator="{ on, attrs }">
          <div v-bind="attrs" v-on="on">
            <v-btn-toggle v-model="filterType" dense mandatory>
              <v-btn value="validator">{{ t('eth2_page.toggle.key') }}</v-btn>
              <v-btn value="address">
                {{ t('eth2_page.toggle.depositor') }}
              </v-btn>
            </v-btn-toggle>
          </div>
        </template>
        <span>{{ t('eth2_page.toggle.hint') }}</span>
      </v-tooltip>
    </v-col>
    <v-col>
      <v-row class="ml-8">
        <v-col>
          <eth2-validator-filter
            :value="value"
            :filter-type="filterType"
            @input="emit('input', $event)"
          />
        </v-col>
        <v-col>
          <eth-validator-range-filter
            @update:period="emit('update:period', $event)"
          />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
