<script setup lang="ts">
const { t } = useI18n();

const emit = defineEmits<{
  (e: 'updated'): void;
}>();

const updated = () => emit('updated');

const showMenu: Ref<boolean> = ref(false);
</script>

<template>
  <v-menu
    v-model="showMenu"
    max-width="500px"
    min-width="280px"
    left
    :close-on-content-click="false"
  >
    <template #activator="{ on }">
      <menu-tooltip-button
        :tooltip="t('statistics_graph_settings.tooltip')"
        class-name="graph-period"
        :on-menu="on"
      >
        <v-icon>mdi-dots-vertical</v-icon>
      </menu-tooltip-button>
    </template>

    <card>
      <ssf-graph-multiplier-setting @updated="updated()" />
      <v-divider class="my-4" />
      <infer-zero-timed-balances-setting @updated="updated()" />

      <template #buttons>
        <v-spacer />
        <v-btn depressed color="primary" @click="showMenu = false">
          {{ t('common.actions.close') }}
        </v-btn>
      </template>
    </card>
  </v-menu>
</template>
