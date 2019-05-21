<template>
  <div class="jconfirm jconfirm-light jconfirm-open">
    <div
      class="jconfirm-bg"
      style="transition-duration: 0.4s; transition-timing-function: cubic-bezier(0.36, 0.55, 0.19, 1);"
    ></div>
    <div class="jconfirm-scrollpane">
      <div class="jconfirm-row">
        <div class="jconfirm-cell">
          <div
            class="jconfirm-holder"
            style="padding-top: 40px; padding-bottom: 40px;"
          >
            <div class="jc-bs3-container container">
              <div
                class="jc-bs3-row row justify-content-md-center justify-content-sm-center justify-content-xs-center justify-content-lg-center"
              >
                <div
                  class="jconfirm-box-container jconfirm-animated col-md-4 col-md-offset-4 col-sm-6 col-sm-offset-3 col-xs-10 col-xs-offset-1 jconfirm-no-transition"
                  style="transform: translate(0px, 0px); transition-duration: 0.4s; transition-timing-function: cubic-bezier(0.36, 0.55, 0.19, 1);"
                >
                  <div
                    class="jconfirm-box jconfirm-hilight-shake jconfirm-type-default jconfirm-type-animated"
                    role="dialog"
                    aria-labelledby="jconfirm-box89620"
                    tabindex="-1"
                    style="transition-duration: 0.4s; transition-timing-function: cubic-bezier(0.36, 0.55, 0.19, 1); transition-property: all, margin;"
                  >
                    <div class="jconfirm-closeIcon" style="display: none;">
                      ×
                    </div>
                    <div class="jconfirm-title-c">
                      <span class="jconfirm-icon-c"></span
                      ><span class="jconfirm-title">Create New Account</span>
                    </div>
                    <div
                      class="jconfirm-content-pane no-scroll"
                      style="transition-duration: 0.4s; transition-timing-function: cubic-bezier(0.36, 0.55, 0.19, 1); height: 245px; max-height: 1168px;"
                    >
                      <div id="jconfirm-box89620" class="jconfirm-content">
                        <div>
                          <div class="form-group input-group">
                            <span class="input-group-addon">User Name:</span
                            ><input
                              id="user_name_entry"
                              v-model="username"
                              class="form-control"
                              placeholder="A name for your user -- only used locally"
                              type="text"
                            />
                          </div>
                          <div class="form-group input-group">
                            <span class="input-group-addon">Password:</span
                            ><input
                              id="password_entry"
                              v-model="password"
                              class="form-control"
                              placeholder="Password to encrypt your data with"
                              type="password"
                            />
                          </div>
                          <div class="form-group input-group">
                            <span class="input-group-addon"
                              >Repeat Password:</span
                            ><input
                              id="repeat_password_entry"
                              v-model="passwordConfirm"
                              class="form-control"
                              placeholder="Repeat Password"
                              type="password"
                            />
                          </div>
                          <div class="form-group input-group">
                            <span class="input-group-addon">API KEY:</span
                            ><input
                              id="api_key_entry"
                              v-model="apiKey"
                              class="form-control"
                              placeholder="Optional: Only for premium users"
                              type="text"
                            />
                          </div>
                          <div class="form-group input-group">
                            <span class="input-group-addon">API SECRET:</span
                            ><input
                              id="api_secret_entry"
                              v-model="apiSecret"
                              class="form-control"
                              placeholder="Optional: Only for premium users"
                              type="text"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="jconfirm-buttons">
                      <button
                        type="button"
                        class="btn btn-blue"
                        @click="confirm()"
                      >
                        Create
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
import { AccountData } from '@/typing/types';

@Component({})
export default class CreateAccount extends Vue {
  username: string = '';
  password: string = '';
  passwordConfirm: string = '';
  apiKey: string = '';
  apiSecret: string = '';

  confirm() {
    const account: AccountData = {
      username: this.username,
      password: this.password,
      apiKey: this.apiKey,
      apiSecret: this.apiSecret
    };
    this.$emit('confirm', account);
  }

  @Emit()
  cancel() {}
}
</script>

<style scoped></style>
