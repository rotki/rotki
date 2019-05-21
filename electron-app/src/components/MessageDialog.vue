<template>
  <div class="jconfirm jconfirm-light jconfirm-open">
    <div class="jconfirm-bg"></div>
    <div class="jconfirm-scrollpane">
      <div class="jconfirm-row">
        <div class="jconfirm-cell">
          <div class="jconfirm-holder">
            <div class="jc-bs3-container container">
              <div
                class="jc-bs3-row row justify-content-md-center justify-content-sm-center justify-content-xs-center justify-content-lg-center"
              >
                <div
                  class="jconfirm-box-container jconfirm-animated col-md-4 col-md-offset-4 col-sm-6 col-sm-offset-3 col-xs-10 col-xs-offset-1 jconfirm-no-transition"
                >
                  <div
                    class="jconfirm-box jconfirm-hilight-shake jconfirm-type-animated jconfirm-type-red"
                    role="dialog"
                    aria-labelledby="jconfirm-box17117"
                    tabindex="-1"
                  >
                    <div class="jconfirm-closeIcon" style="display: none;">
                      ×
                    </div>
                    <div class="jconfirm-title-c">
                      <span class="jconfirm-icon-c"></span>
                      <span class="jconfirm-title">{{ title }}</span>
                    </div>
                    <div class="jconfirm-content-pane no-scroll">
                      <div id="jconfirm-box17117" class="jconfirm-content">
                        <div>
                          <div>{{ message }}</div>
                        </div>
                      </div>
                    </div>
                    <div class="jconfirm-buttons">
                      <button
                        type="button"
                        class="btn btn-default"
                        @click="confirm()"
                      >
                        ok
                      </button>
                    </div>
                    <div class="jconfirm-clear"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class MessageDialog extends Vue {
  @Prop({ required: true })
  title!: string;
  @Prop({ required: true })
  message!: string;

  @Emit()
  confirm() {}
}
</script>

<style scoped></style>
