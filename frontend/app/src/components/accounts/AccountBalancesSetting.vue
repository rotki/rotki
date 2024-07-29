<script setup lang="ts">
const value = ref<boolean>(false);

const { unifyAccountsTable: enabled } = storeToRefs(useFrontendSettingsStore());

watchImmediate(enabled, () => {
  set(value, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <RuiMenu
    :popper="{ placement: 'bottom-end' }"
    menu-class="max-w-[24rem]"
    close-on-content-click
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="text"
        icon
        size="sm"
        class="!p-2"
        v-bind="attrs"
      >
        <RuiIcon name="settings-3-line" />
      </RuiButton>
    </template>

    <div class="py-2">
      <SettingsOption
        #default="{ updateImmediate }"
        setting="unifyAccountsTable"
        frontend-setting
      >
        <RuiCheckbox
          v-model="value"
          color="primary"
          data-cy="asset-filter-only-show-owned"
          class="mt-0 px-3"
          :label="t('blockchain_balances.unify_accounts_table')"
          hide-details
          @update:model-value="updateImmediate($event)"
        />
      </SettingsOption>
    </div>
  </RuiMenu>
</template>
