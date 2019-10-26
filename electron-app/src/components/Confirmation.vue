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
                    class="jconfirm-box jconfirm-hilight-shake jconfirm-type-default jconfirm-type-animated"
                    role="dialog"
                    aria-labelledby="jconfirm-box9382"
                    tabindex="-1"
                  >
                    <div class="jconfirm-closeIcon" style="display: none;">
                      ×
                    </div>
                    <div class="jconfirm-title-c">
                      <span class="jconfirm-icon-c"></span>
                      <span class="jconfirm-title">
                        Confirmation Required
                      </span>
                    </div>
                    <div class="jconfirm-content-pane no-scroll">
                      <div id="jconfirm-box9382" class="jconfirm-content">
                        <div>
                          Are you sure you want to log out of your current
                          rotkehlchen session?
                        </div>
                      </div>
                    </div>
                    <div class="jconfirm-buttons">
                      <button
                        type="button"
                        class="btn btn-default"
                        @click="confirm()"
                      >
                        confirm
                      </button>
                      <button
                        type="button"
                        class="btn btn-default"
                        @click="cancel()"
                      >
                        cancel
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
import { Component, Emit, Vue } from 'vue-property-decorator';

@Component({})
export default class Confirmation extends Vue {
  @Emit()
  confirm() {}

  @Emit()
  cancel() {}
}
</script>

<style scoped></style>
