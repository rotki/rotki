<template>
  <v-menu
    v-model="menu"
    :nudge-width="150"
    offset-x
    :close-on-content-click="false"
  >
    <template #activator="{ on: menuListeners, attrs }">
      <v-tooltip top>
        <template #activator="{ on: tooltipListeners }">
          <v-btn
            v-bind="attrs"
            icon
            fab
            small
            depressed
            :disabled="loading"
            v-on="{ ...menuListeners, ...tooltipListeners }"
          >
            <v-icon color="primary">mdi-database-refresh</v-icon>
          </v-btn>
        </template>
        <span>
          {{ tooltip }}
        </span>
      </v-tooltip>
    </template>
    <v-card max-width="280px">
      <v-card-title>{{ $t('confirmable_reset.confirm.title') }}</v-card-title>
      <v-card-text>
        <slot>{{ $t('confirmable_reset.confirm.message') }}</slot>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn text @click="menu = false">
          {{ $t('confirmable_reset.confirm.cancel') }}
        </v-btn>
        <v-btn color="primary" text :disabled="disabled" @click="reset()">
          {{ $t('confirmable_reset.confirm.confirm') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>

<script lang="ts">
import { defineComponent, ref } from '@vue/composition-api';
import { set } from '@vueuse/core';

export default defineComponent({
  name: 'ConfirmableReset',
  props: {
    tooltip: { required: false, type: String, default: '' },
    loading: { required: false, type: Boolean, default: false },
    disabled: { required: false, type: Boolean, default: false }
  },
  emits: ['reset'],
  setup(_, { emit }) {
    const menu = ref<boolean>(false);

    const reset = () => {
      set(menu, false);
      emit('reset');
    };

    return {
      menu,
      reset
    };
  }
});
</script>
