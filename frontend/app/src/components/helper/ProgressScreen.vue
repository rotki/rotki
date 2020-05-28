<template>
  <v-col cols="12" class="progress-screen__progress">
    <v-row
      v-if="progress !== -1"
      align="center"
      justify="center"
      class="font-weight-light progress-screen__progress__percentage"
    >
      {{ progress }} %
    </v-row>
    <v-row
      align="center"
      justify="center"
      class="progress-screen__progress__progress"
    >
      <v-col cols="10">
        <v-progress-linear
          v-if="progress !== -1"
          class="text-center"
          rounded
          height="16"
          color="primary"
          :value="progress"
        >
        </v-progress-linear>
        <div v-else class="progress-screen__progress-indeterminate">
          <v-progress-circular
            rounded
            indeterminate
            :size="70"
            color="primary"
          ></v-progress-circular>
        </div>
      </v-col>
    </v-row>
    <v-row align="center" justify="center">
      <p
        class="text-center font-weight-light progress-screen__progress__description"
      >
        <slot name="message"></slot>
      </p>
    </v-row>
    <v-row align="center" justify="center">
      <v-col cols="4">
        <v-divider></v-divider>
      </v-col>
    </v-row>
    <v-row
      align="center"
      justify="center"
      class="progress-screen__progress__warning"
    >
      <div class="font-weight-light subtitle-2">
        <slot></slot>
      </div>
    </v-row>
  </v-col>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class ProgressScreen extends Vue {
  @Prop({ required: false, default: -1 })
  progress!: number;
}
</script>
<style scoped lang="scss">
.progress-screen {
  &__progress-indeterminate {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin-bottom: 80px;
  }

  &__progress {
    margin-top: 140px;
    height: 100%;
    min-height: 300px;

    &__progress {
      min-height: 80px;
    }

    &__percentage {
      font-size: 46px;
    }

    &__description {
      font-size: 16px;
    }

    &__warning {
      margin-top: 30px;
    }
  }
}
</style>
