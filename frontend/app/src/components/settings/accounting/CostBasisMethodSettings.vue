<template>
  <v-select
    v-bind="$attrs"
    item-text="value"
    item-value="value"
    outlined
    persistent-hint
    :items="selections"
    v-on="$listeners"
  >
    <template #item="{ item, attrs, on }">
      <v-list-item v-bind="attrs" v-on="on">
        <v-list-item-content>
          <v-list-item-title :class="$style.title">
            {{ item.value }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ item.text }}
          </v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>
    </template>
    <template #selection="{ item }">
      <span :class="$style.title">{{ item.value }}</span>
    </template>
  </v-select>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import i18n from '@/i18n';
import { CostBasisMethod } from '@/types/user';
export default defineComponent({
  name: 'CostBasisMethodSettings',
  setup() {
    const selections = [
      {
        value: CostBasisMethod.Fifo,
        text: i18n.t('account_settings.cost_basis_method_settings.labels.fifo')
      },
      {
        value: CostBasisMethod.Lifo,
        text: i18n.t('account_settings.cost_basis_method_settings.labels.lifo')
      }
    ];

    return {
      selections
    };
  }
});
</script>
<style module lang="scss">
.title {
  text-transform: uppercase;
  font-weight: 500;
}
</style>
