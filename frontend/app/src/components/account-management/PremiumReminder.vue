<template>
  <v-card v-if="display" light max-width="500" class="mx-auto premium-reminder">
    <v-card-title class="premium-reminder__title">
      {{ $t('premium_reminder.title') }}
    </v-card-title>
    <v-card-text>
      <v-row class="mx-auto text-justify">
        <v-col cols="auto" align-self="center">
          <v-icon color="success" size="48">
            mdi-information
          </v-icon>
        </v-col>
        <v-col cols="10">{{ $t('premium_reminder.description') }}</v-col>
      </v-row>
    </v-card-text>
    <v-card-actions>
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
        class="premium-reminder__buttons__confirm"
        @click="upgrade"
      >
        {{ $t('premium_reminder.buttons.upgrade') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class PremiumReminder extends Vue {
  @Prop({ required: true, type: Boolean })
  display!: boolean;
  @Emit()
  loginComplete() {}
  @Emit()
  upgrade() {}

  keyHandler(event: KeyboardEvent) {
    if (!this.display) {
      return;
    }

    const keys = ['Escape', 'Esc'];
    if (!keys.includes(event.key)) {
      return;
    }
    this.loginComplete();
  }

  created() {
    document.addEventListener('keydown', this.keyHandler);
  }

  destroyed() {
    document.removeEventListener('keydown', this.keyHandler);
  }
}
</script>
