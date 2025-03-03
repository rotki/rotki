<script setup lang="ts">
import SummaryCardCreateButton from '@/components/dashboard/summary-card/SummaryCardCreateButton.vue';

const { t } = useI18n();
const router = useRouter();

const blockchainCategories = [
  {
    icon: 'lu-evm-accounts',
    label: t('dashboard.blockchain_balances.categories.evm'),
    path: '/accounts/evm/accounts',
  },
  {
    icon: 'lu-bitcoin-accounts',
    label: t('dashboard.blockchain_balances.categories.bitcoin'),
    path: '/accounts/bitcoin',
  },
  {
    icon: 'lu-substrate-accounts',
    label: t('dashboard.blockchain_balances.categories.substrate'),
    path: '/accounts/substrate',
  },
];

function addBlockchainAccount(path: string) {
  router.push({
    path,
    query: {
      add: 'true',
    },
  });
}
</script>

<template>
  <RuiMenu wrapper-class="w-full">
    <template #activator="{ attrs }">
      <SummaryCardCreateButton v-bind="attrs">
        {{ t('dashboard.blockchain_balances.add') }}
      </SummaryCardCreateButton>
    </template>
    <div class="py-2">
      <RuiButton
        v-for="blockchainCategory in blockchainCategories"
        :key="blockchainCategory.path"
        variant="list"
        @click="addBlockchainAccount(blockchainCategory.path)"
      >
        <template #prepend>
          <RuiIcon :name="blockchainCategory.icon" />
        </template>
        {{ blockchainCategory.label }}
      </RuiButton>
    </div>
  </RuiMenu>
</template>
