import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { assert } from '@rotki/common';
import { type McpServerStatus, StarlingServiceStatus } from '@shared/ipc';
import { createMock } from '@test/utils/create-mock';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { PremiumFeature } from '@/modules/session/types';
import McpServerSetting from '@/modules/settings/backend/McpServerSetting.vue';
import { setMcpServerState } from '@/modules/settings/backend/use-mcp-server-state';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { McpPrivacyMode } from '@/modules/settings/types/mcp';

const mocks = vi.hoisted(() => ({
  getMcpServerStatus: vi.fn(),
  isPackaged: true,
  setMcpAutoStart: vi.fn(),
  startMcpServer: vi.fn(),
  stopMcpServer: vi.fn(),
}));

/** Token minting is an API call, not an interop member. */
const mcpApi = vi.hoisted(() => ({ generateMcpToken: vi.fn() }));

/**
 * The component drives the supervisor through the control client, never through
 * a runtime check of its own, so the transport is what gets stubbed here.
 */
const control = vi.hoisted(() => ({
  available: vi.fn(),
  probe: vi.fn(),
  serviceInfo: vi.fn(),
  setServiceAutostart: vi.fn(),
  setServiceRunning: vi.fn(),
  supportsOptions: true,
}));

vi.mock('@/modules/settings/api/use-mcp-api', () => ({
  useMcpApi: (): Record<string, unknown> => ({
    generateMcpToken: mcpApi.generateMcpToken,
  }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): ReturnType<typeof useInterop> => createMock<ReturnType<typeof useInterop>>({
    ...mocks,
  }),
}));

vi.mock('@/modules/core/control/use-control', () => ({
  useControl: (): Record<string, unknown> => ({
    available: control.available(),
    probe: control.probe,
    serviceInfo: control.serviceInfo,
    setServiceAutostart: control.setServiceAutostart,
    setServiceRunning: control.setServiceRunning,
    supportsOptions: control.supportsOptions,
  }),
}));

const stoppedStatus: McpServerStatus = {
  autoStart: false,
  endpoint: 'http://127.0.0.1:4445/mcp',
  state: StarlingServiceStatus.IDLE,
};

/** Control exists and answers; the ordinary case for desktop and docker alike. */
function controlAvailable(supportsOptions: boolean): void {
  control.supportsOptions = supportsOptions;
  control.available.mockReturnValue(ref(true));
  control.probe.mockResolvedValue(true);
}

/** No supervisor to talk to: the plain web build, or docker with no session key. */
function controlUnavailable(): void {
  control.supportsOptions = false;
  control.available.mockReturnValue(ref(false));
  control.probe.mockResolvedValue(false);
}

function createWrapper(): VueWrapper<InstanceType<typeof McpServerSetting>> {
  return mount(McpServerSetting, {
    global: {
      stubs: {
        CopyTooltip: {
          props: ['value'],
          template: '<div class="copy-tooltip" :data-value="value"><slot /><slot name="label" /></div>',
        },
        RuiAlert: {
          template: '<div class="rui-alert"><slot /></div>',
        },
        RuiButton: {
          emits: ['click'],
          props: ['disabled'],
          template: '<button v-bind="$attrs" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
        },
        RuiChip: {
          template: '<span class="rui-chip"><slot /></span>',
        },
        RuiIcon: true,
        RuiRadio: {
          props: ['value'],
          template: '<label class="rui-radio"><slot /></label>',
        },
        RuiRadioGroup: {
          props: ['disabled', 'errorMessages', 'modelValue', 'successMessages'],
          template: '<div class="rui-radio-group"><slot /></div>',
        },
        RuiSwitch: {
          emits: ['update:modelValue'],
          props: ['disabled', 'modelValue'],
          // `data-model-value` exposes what the switch is bound to, so a test can
          // tell the stored value from the one that was clicked.
          template: '<button v-bind="$attrs" class="rui-switch" :data-model-value="modelValue" :disabled="disabled" @click="$emit(\'update:modelValue\', !modelValue)" />',
        },
        GetPremiumPlaceholder: {
          props: ['description', 'minimumTier', 'title'],
          template: '<div class="get-premium-placeholder" :data-minimum-tier="minimumTier">{{ title }}{{ description }}</div>',
        },
        SettingsItem: {
          template: '<section><slot name="title" /><slot name="subtitle" /><slot /></section>',
        },
      },
    },
  });
}

/**
 * The privacy preview's cells for one field, as [on-chain swap, exchange deposit]. Anchored on the
 * field name rather than a row index so a reordered preview fails loudly instead of silently
 * asserting the wrong row.
 */
function previewRow(wrapper: VueWrapper<InstanceType<typeof McpServerSetting>>, field: string): string[] {
  // The group caption rows carry no header cell, hence the exists() guard before reading it.
  const row = wrapper.findAll('tbody tr').find((entry) => {
    const header = entry.find('th');
    return header.exists() && header.text() === field;
  });
  assert(row, `the privacy preview has no ${field} row`);
  return row.findAll('td').map(cell => cell.text());
}

/** Every column name the preview claims the assistant receives, in render order. */
function previewFields(wrapper: VueWrapper<InstanceType<typeof McpServerSetting>>): string[] {
  return wrapper.findAll('tbody tr th').map(header => header.text());
}

/** What the auto-start switch is actually bound to, rather than what was clicked. */
function autoStartValue(wrapper: VueWrapper<InstanceType<typeof McpServerSetting>>): boolean {
  return wrapper.find('[data-testid="mcp-auto-start"]').attributes('data-model-value') === 'true';
}

function grantMcpAccess(enabled: boolean, minimumTier = 'Basic'): void {
  const { capabilities, premium } = storeToRefs(usePremiumStore());
  set(premium, true);
  set(capabilities, {
    currentTier: enabled ? 'Basic' : 'Supporter',
    [PremiumFeature.MCP]: { enabled, minimumTier },
  });
}

function revokePremium(): void {
  const { capabilities, premium } = storeToRefs(usePremiumStore());
  set(premium, false);
  set(capabilities, undefined);
}

describe('mcpServerSetting', () => {
  let storedAutoStart = false;

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.stubEnv('VITE_DOCKER', 'false');
    grantMcpAccess(true);
    mocks.isPackaged = true;
    controlAvailable(true);
    // The supervisor is the source of truth for both facts, so the stub keeps a
    // stored preference the way starling does: a write changes what a later read
    // answers, and the component is expected to read it back.
    storedAutoStart = false;
    control.serviceInfo.mockImplementation(async () => ({
      autostart: storedAutoStart,
      state: StarlingServiceStatus.IDLE,
    }));
    control.setServiceAutostart.mockImplementation(async (_service: string, autostart: boolean) => {
      storedAutoStart = autostart;
    });
    control.setServiceRunning.mockImplementation(
      async (_service: string, running: boolean) =>
        (running ? StarlingServiceStatus.READY : StarlingServiceStatus.IDLE),
    );
    mcpApi.generateMcpToken.mockResolvedValue({
      accessToken: 'generated-mcp-token',
      expiresAt: 1_800_000_000,
      tokenType: 'Bearer',
    });
    setMcpServerState(undefined);
    mocks.getMcpServerStatus.mockResolvedValue(stoppedStatus);
  });

  it('should show the managed endpoint and stopped state by default', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('code').text()).toBe(stoppedStatus.endpoint);
    expect(wrapper.find('.copy-tooltip').attributes('data-value')).toBe(stoppedStatus.endpoint);
    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.status.stopped');
  });

  it('should offer every privacy mode with an explanation', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    const selector = wrapper.find('[data-testid="mcp-privacy-mode"]');
    expect(selector.exists()).toBe(true);
    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.privacy_mode.label');
    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.privacy_mode.hint');
    expect(selector.text()).toContain('backend_settings.settings.mcp_server.privacy_mode.strict.description');
    expect(selector.text()).toContain('backend_settings.settings.mcp_server.privacy_mode.balanced.description');
    expect(selector.text()).toContain('backend_settings.settings.mcp_server.privacy_mode.raw.description');
    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.privacy_mode.preview.title');
    // Balanced keeps the venue name readable under its own column, alongside the hash every
    // identifier gets.
    expect(previewRow(wrapper, 'location_label')).toStrictEqual([
      'backend_settings.settings.mcp_server.privacy_mode.preview.not_set',
      'kraken',
    ]);
    expect(previewRow(wrapper, 'location_label_hash')).toStrictEqual([
      'anon_5c4efe77c7146ef8',
      'anon_b43a5d4cd838add9',
    ]);
    expect(selector.findAll('.rui-radio')).toHaveLength(3);
    expect(selector.findAll('.rui-radio').every(radio => (
      radio.element.parentElement === selector.element
    ))).toBe(true);
  });

  /**
   * The one field that separates balanced from strict. `READABLE_LOCATION_LABELS` in
   * rotkehlchen/mcp/analytics.py lets a location label through only when it is exactly a rotki
   * location name, so the exchange row stays readable in balanced and is hashed in strict; the
   * on-chain row is address-shaped and is hashed in both.
   */
  it('should mask the exchange account label only in strict mode', async () => {
    const repo = useSettingsRepo();
    repo.updateGeneral({ ...repo.general, mcpPrivacyMode: McpPrivacyMode.STRICT });

    const wrapper = createWrapper();
    await flushPromises();

    // "not sent", not "not set": strict emits no such column, so querying it would fail rather
    // than return null.
    expect(previewRow(wrapper, 'location_label')).toStrictEqual([
      'backend_settings.settings.mcp_server.privacy_mode.preview.not_sent',
      'backend_settings.settings.mcp_server.privacy_mode.preview.not_sent',
    ]);
    expect(previewRow(wrapper, 'location_label_hash')).toStrictEqual([
      'anon_5c4efe77c7146ef8',
      'anon_b43a5d4cd838add9',
    ]);
  });

  /**
   * Outside raw an identifier moves to `<column>_hash` and its own column is dropped, so a preview
   * that still labelled the hash `tx_hash` would send someone to write SQL against a column the
   * assistant never received.
   */
  it('should name masked identifier columns as the assistant sees them', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    const fields = previewFields(wrapper);
    expect(fields).toContain('tx_hash_hash');
    expect(fields).not.toContain('tx_hash');
  });

  it('should warn and preview unmasked fields in raw mode', async () => {
    const repo = useSettingsRepo();
    repo.updateGeneral({ ...repo.general, mcpPrivacyMode: McpPrivacyMode.RAW });

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.text()).toContain(
      'backend_settings.settings.mcp_server.privacy_mode.raw_warning.title',
    );
    expect(wrapper.text()).toContain('0x9C5083…5dAC5');
    expect(wrapper.text()).toContain('quarterly rebalance');
  });

  it('should persist auto-start without starting the server', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(autoStartValue(wrapper)).toBe(false);

    await wrapper.find('[data-testid="mcp-auto-start"]').trigger('click');
    await flushPromises();

    expect(control.setServiceAutostart).toHaveBeenCalledWith('mcp', true);
    expect(control.setServiceRunning).not.toHaveBeenCalled();
    // Read back from the supervisor, not from the click.
    expect(autoStartValue(wrapper)).toBe(true);
  });

  it('should leave the auto-start switch where it was when the write is refused', async () => {
    // The failure mode this rules out: a switch that shows the new position while
    // the next restart still uses the old one.
    control.setServiceAutostart.mockRejectedValueOnce(new Error('read-only file system'));
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid="mcp-auto-start"]').trigger('click');
    await flushPromises();

    expect(autoStartValue(wrapper)).toBe(false);
    expect(wrapper.text()).toContain('read-only file system');
  });

  it('should start and stop the server on demand', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    const lifecycleButton = wrapper.find('[data-testid="mcp-lifecycle"]');
    expect(lifecycleButton.attributes('color')).toBe('primary');

    await lifecycleButton.trigger('click');
    await flushPromises();
    expect(control.setServiceRunning).toHaveBeenLastCalledWith('mcp', true);
    expect(lifecycleButton.attributes('color')).toBe('error');

    await lifecycleButton.trigger('click');
    await flushPromises();
    expect(control.setServiceRunning).toHaveBeenLastCalledWith('mcp', false);
    expect(lifecycleButton.attributes('color')).toBe('primary');
  });

  it('should disable lifecycle control when MCP is unavailable', async () => {
    control.serviceInfo.mockResolvedValueOnce({ autostart: false, state: StarlingServiceStatus.UNAVAILABLE });
    const wrapper = createWrapper();
    await flushPromises();

    const lifecycleButton = wrapper.find('[data-testid="mcp-lifecycle"]');
    expect(lifecycleButton.attributes('disabled')).toBeDefined();
    await lifecycleButton.trigger('click');

    expect(control.setServiceRunning).not.toHaveBeenCalled();
  });

  it('should not offer the auto-start switch when the supervisor does not manage MCP', async () => {
    // Offering it would post a write the supervisor refuses, and show the user
    // its raw "invalid service" string.
    control.serviceInfo.mockResolvedValue({ autostart: false, state: StarlingServiceStatus.UNAVAILABLE });
    const wrapper = createWrapper();
    await flushPromises();

    const toggle = wrapper.find('[data-testid="mcp-auto-start"]');
    expect(toggle.attributes('disabled')).toBeDefined();
    await toggle.trigger('click');
    await flushPromises();

    expect(control.setServiceAutostart).not.toHaveBeenCalled();
  });

  it('should keep the status chip current across an auto-start toggle', async () => {
    // The read-back carries the state as well, so a server that stopped while the
    // page was open is not reported as running afterwards.
    const wrapper = createWrapper();
    await flushPromises();
    control.serviceInfo.mockResolvedValue({ autostart: true, state: StarlingServiceStatus.READY });

    await wrapper.find('[data-testid="mcp-auto-start"]').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.status.running');
  });

  it('should show a failed state when the managed MCP service crashes', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    setMcpServerState(StarlingServiceStatus.FAILED);
    await nextTick();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.status.failed');
  });

  it('should show lifecycle errors and refresh the service state', async () => {
    control.setServiceRunning.mockRejectedValueOnce(new Error('start failed'));
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid="mcp-lifecycle"]').trigger('click');
    await flushPromises();

    expect(control.serviceInfo).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain('start failed');
  });

  it('should show a loading state before the initial status resolves', async () => {
    control.serviceInfo.mockReturnValueOnce(new Promise(() => {}));

    const wrapper = createWrapper();
    await nextTick();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.status.loading');
  });

  it('should show the desktop-only message in the plain web build', async () => {
    mocks.isPackaged = false;
    controlUnavailable();

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.desktop_only');
    expect(control.serviceInfo).not.toHaveBeenCalled();
  });

  it('should explain the absent control endpoint in an unauthenticated Docker deployment', async () => {
    // starling only mounts `/_control` when a session key is configured, so the
    // panel must say why rather than offer buttons that would 404.
    vi.stubEnv('VITE_DOCKER', 'true');
    mocks.isPackaged = false;
    controlUnavailable();

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.control_unavailable');
    expect(wrapper.find('[data-testid="mcp-lifecycle"]').exists()).toBe(false);
    expect(control.serviceInfo).not.toHaveBeenCalled();
  });

  it('should drive the MCP lifecycle in Docker, not just describe it', async () => {
    vi.stubEnv('VITE_DOCKER', 'true');
    mocks.isPackaged = false;
    controlAvailable(false);

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('code').text()).toBe(`${window.location.origin}/mcp`);
    await wrapper.find('[data-testid="mcp-lifecycle"]').trigger('click');
    await flushPromises();

    expect(control.setServiceRunning).toHaveBeenCalledWith('mcp', true);
    expect(mocks.getMcpServerStatus).not.toHaveBeenCalled();
  });

  it('should let a Docker deployment opt out of starting MCP with the tree', async () => {
    vi.stubEnv('VITE_DOCKER', 'true');
    mocks.isPackaged = false;
    controlAvailable(false);
    storedAutoStart = true;

    const wrapper = createWrapper();
    await flushPromises();

    expect(autoStartValue(wrapper)).toBe(true);
    await wrapper.find('[data-testid="mcp-auto-start"]').trigger('click');
    await flushPromises();

    expect(control.setServiceAutostart).toHaveBeenCalledWith('mcp', false);
    expect(autoStartValue(wrapper)).toBe(false);
    // The preference belongs to the supervisor here, not to Electron.
    expect(mocks.setMcpAutoStart).not.toHaveBeenCalled();
  });

  it('should generate and display a bearer token in Docker', async () => {
    vi.stubEnv('VITE_DOCKER', 'true');
    mocks.isPackaged = false;
    controlAvailable(false);

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.text()).not.toContain('backend_settings.settings.mcp_server.desktop_only');

    await wrapper.find('[data-testid="mcp-generate-token"]').trigger('click');
    await flushPromises();

    expect(mcpApi.generateMcpToken).toHaveBeenCalledOnce();
    expect(wrapper.find('[data-testid="mcp-token"]').text()).toBe('••••••••••••••••');
    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.token_expiry_hint');

    await wrapper.find('[data-testid="mcp-toggle-token"]').trigger('click');
    expect(wrapper.find('[data-testid="mcp-token"]').text()).toBe('generated-mcp-token');
  });

  it('should show token generation errors separately in Docker', async () => {
    vi.stubEnv('VITE_DOCKER', 'true');
    mocks.isPackaged = false;
    controlAvailable(false);
    mcpApi.generateMcpToken.mockRejectedValueOnce(new Error('token failed'));

    const wrapper = createWrapper();
    await flushPromises();
    await wrapper.find('[data-testid="mcp-generate-token"]').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain(
      'backend_settings.settings.mcp_server.token_error',
    );
    expect(wrapper.text()).toContain('token failed');
    expect(wrapper.text()).not.toContain('backend_settings.settings.mcp_server.error');
  });

  it('should not show the premium gate when MCP is unlocked', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid="mcp-premium-gate"]').exists()).toBe(false);
  });

  it('should tell a premium user their plan is insufficient, with the required tier', async () => {
    grantMcpAccess(false);

    const wrapper = createWrapper();
    await flushPromises();

    const gate = wrapper.find('[data-testid="mcp-premium-gate"]');
    expect(gate.exists()).toBe(true);
    expect(gate.text()).toContain('backend_settings.settings.mcp_server.premium_plan_title');
    expect(gate.text()).not.toContain('backend_settings.settings.mcp_server.premium_title');
    expect(gate.find('.get-premium-placeholder').attributes('data-minimum-tier')).toBe('Basic');
  });

  it('should ask a user without a subscription to subscribe', async () => {
    revokePremium();

    const wrapper = createWrapper();
    await flushPromises();

    const gate = wrapper.find('[data-testid="mcp-premium-gate"]');
    expect(gate.exists()).toBe(true);
    expect(gate.text()).toContain('backend_settings.settings.mcp_server.premium_title');
    expect(gate.text()).not.toContain('backend_settings.settings.mcp_server.premium_plan_title');
    // no capabilities are fetched without a subscription, so there is no tier to name
    expect(gate.text()).toContain('backend_settings.settings.mcp_server.premium_description');
  });

  it('should hide the lifecycle controls when MCP is locked', async () => {
    grantMcpAccess(false);

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid="mcp-lifecycle"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="mcp-auto-start"]').exists()).toBe(false);
  });

  it('should hide token generation in Docker when MCP is locked', async () => {
    vi.stubEnv('VITE_DOCKER', 'true');
    mocks.isPackaged = false;
    grantMcpAccess(false);

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid="mcp-premium-gate"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="mcp-generate-token"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain('backend_settings.settings.mcp_server.docker_description');
  });

  it('should show the desktop-only message instead of the gate in the web build', async () => {
    grantMcpAccess(false);
    mocks.isPackaged = false;
    controlUnavailable();

    const wrapper = createWrapper();
    await flushPromises();

    // there is no server to run here for anyone, so the answer is "not here", not "buy premium"
    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.desktop_only');
    expect(wrapper.find('[data-testid="mcp-premium-gate"]').exists()).toBe(false);
  });

  it('should reveal working controls once capabilities unlock MCP after mount', async () => {
    grantMcpAccess(false);

    const wrapper = createWrapper();
    await flushPromises();
    expect(wrapper.find('[data-testid="mcp-lifecycle"]').exists()).toBe(false);

    // capabilities arrive after mount, so the status is loaded regardless of the gate:
    // unlocking must not leave the user with controls that have no state to act on
    grantMcpAccess(true);
    await flushPromises();

    expect(wrapper.find('[data-testid="mcp-lifecycle"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="mcp-lifecycle"]').attributes('disabled')).toBeUndefined();
  });
});
