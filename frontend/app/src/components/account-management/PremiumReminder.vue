<template>
  <v-card v-if="display" light max-width="500" class="mx-auto premium-reminder">
    <v-card-title class="premium-reminder__title">
      {{ $t('premium_reminder.title') }}
    </v-card-title>
    <v-card-text>
      <v-row class="mx-auto text-justify">
        <v-col cols="auto" align-self="center">
          <v-icon color="success" size="48"> mdi-information </v-icon>
        </v-col>
        <v-col cols="10">{{ $t('premium_reminder.description') }}</v-col>
      </v-row>
    </v-card-text>
    <v-card-actions class="pa-4">
      <v-spacer />
      <v-btn
        color="primary"
        class="premium-reminder__buttons__cancel"
        depressed
        outlined
        @click="loginComplete"
      >
        {{ $t('premium_reminder.buttons.close') }}
      </v-btn>
      <v-btn
        color="primary"
        depressed
        target="_blank"
        :href="$interop.isPackaged ? undefined : $interop.premiumURL"
        class="premium-reminder__buttons__confirm"
        @click="upgrade"
      >
        {{ $t('premium_reminder.buttons.upgrade') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
<script lang="ts">
import {
  defineComponent,
  onBeforeMount,
  onBeforeUnmount,
  toRefs
} from '@vue/composition-api';

export default defineComponent({
  name: 'PremiumReminder',
  props: {
    display: { required: true, type: Boolean }
  },
  emits: ['login-complete', 'upgrade'],
  setup(props, { emit }) {
    const { display } = toRefs(props);

    const loginComplete = () => emit('login-complete');
    const upgrade = () => emit('upgrade');

    const keyHandler = (event: KeyboardEvent) => {
      if (!display.value) {
        return;
      }

      const keys = ['Escape', 'Esc'];
      if (!keys.includes(event.key)) {
        return;
      }
      loginComplete();
    };
    onBeforeMount(() => {
      document.addEventListener('keydown', keyHandler);
    });
    onBeforeUnmount(() => {
      document.removeEventListener('keydown', keyHandler);
    });

    return { upgrade, loginComplete };
  }
});
</script>
