<template>
  <div class="error-screen">
    <div>
      <v-icon size="120" color="error">fa-exclamation-circle</v-icon>
    </div>
    <div class="error-screen__title">
      <h1>Rotki failed to start</h1>
    </div>
    <v-divider width="150"></v-divider>
    <div class="font-weight-light error-screen__description">{{ message }}</div>
    <div>
      <v-btn depressed color="primary" @click="terminate()">
        Terminate
      </v-btn>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { remote } from 'electron';

@Component({})
export default class ErrorScreen extends Vue {
  @Prop({ required: true })
  message!: string;

  terminate() {
    remote.getCurrentWindow().close();
  }
}
</script>

<style scoped lang="scss">
.error-screen {
  background-color: white;
  height: 100%;
  width: 100%;
  z-index: 99999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.error-screen__title {
  margin-top: 25px;
  margin-bottom: 5px;
}

.error-screen__description {
  margin-top: 50px;
  margin-bottom: 80px;
}
</style>
