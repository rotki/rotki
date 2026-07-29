import type { McpServerStatus } from '@shared/ipc';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import McpServerSetting from '@/modules/settings/backend/McpServerSetting.vue';
import { setMcpServerState } from '@/modules/settings/backend/use-mcp-server-state';

const mocks = vi.hoisted(() => ({
  generateMcpToken: vi.fn(),
  getMcpServerStatus: vi.fn(),
  isPackaged: true,
  setMcpAutoStart: vi.fn(),
  startMcpServer: vi.fn(),
  stopMcpServer: vi.fn(),
}));

vi.mock('@/modules/settings/api/use-mcp-api', () => ({
  useMcpApi: (): Record<string, unknown> => ({
    generateMcpToken: mocks.generateMcpToken,
  }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): Record<string, unknown> => ({
    ...mocks,
  }),
}));

const stoppedStatus: McpServerStatus = {
  autoStart: false,
  endpoint: 'http://127.0.0.1:4445/mcp',
  state: 'Idle',
};

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
        RuiSwitch: {
          emits: ['update:modelValue'],
          props: ['disabled', 'modelValue'],
          template: '<button v-bind="$attrs" class="rui-switch" :disabled="disabled" @click="$emit(\'update:modelValue\', !modelValue)" />',
        },
        SettingsItem: {
          template: '<section><slot name="title" /><slot name="subtitle" /><slot /></section>',
        },
      },
    },
  });
}

describe('mcpServerSetting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv('VITE_DOCKER', 'false');
    mocks.isPackaged = true;
    mocks.generateMcpToken.mockResolvedValue({
      accessToken: 'generated-mcp-token',
      expiresAt: 1_800_000_000,
      tokenType: 'Bearer',
    });
    setMcpServerState(undefined);
    mocks.getMcpServerStatus.mockResolvedValue(stoppedStatus);
    mocks.setMcpAutoStart.mockImplementation(async (enabled: boolean) => ({
      ...stoppedStatus,
      autoStart: enabled,
    }));
    mocks.startMcpServer.mockResolvedValue({ ...stoppedStatus, state: 'Ready' });
    mocks.stopMcpServer.mockResolvedValue(stoppedStatus);
  });

  it('should show the managed endpoint and stopped state by default', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(mocks.getMcpServerStatus).toHaveBeenCalledOnce();
    expect(wrapper.find('code').text()).toBe(stoppedStatus.endpoint);
    expect(wrapper.find('.copy-tooltip').attributes('data-value')).toBe(stoppedStatus.endpoint);
    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.status.stopped');
  });

  it('should persist auto-start without starting the server', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid="mcp-auto-start"]').trigger('click');
    await flushPromises();

    expect(mocks.setMcpAutoStart).toHaveBeenCalledWith(true);
    expect(mocks.startMcpServer).not.toHaveBeenCalled();
  });

  it('should start and stop the server on demand', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid="mcp-lifecycle"]').trigger('click');
    await flushPromises();
    expect(mocks.startMcpServer).toHaveBeenCalledOnce();

    await wrapper.find('[data-testid="mcp-lifecycle"]').trigger('click');
    await flushPromises();
    expect(mocks.stopMcpServer).toHaveBeenCalledOnce();
  });

  it('should disable lifecycle control when MCP is unavailable', async () => {
    mocks.getMcpServerStatus.mockResolvedValueOnce({ ...stoppedStatus, state: 'Unavailable' });
    const wrapper = createWrapper();
    await flushPromises();

    const lifecycleButton = wrapper.find('[data-testid="mcp-lifecycle"]');
    expect(lifecycleButton.attributes('disabled')).toBeDefined();
    await lifecycleButton.trigger('click');

    expect(mocks.startMcpServer).not.toHaveBeenCalled();
    expect(mocks.stopMcpServer).not.toHaveBeenCalled();
  });

  it('should show a failed state when the managed MCP service crashes', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    setMcpServerState('Failed');
    await nextTick();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.status.failed');
  });

  it('should show lifecycle errors and refresh the service state', async () => {
    mocks.startMcpServer.mockRejectedValueOnce(new Error('start failed'));
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid="mcp-lifecycle"]').trigger('click');
    await flushPromises();

    expect(mocks.getMcpServerStatus).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain('start failed');
  });

  it('should show a loading state before the initial status resolves', async () => {
    mocks.getMcpServerStatus.mockReturnValueOnce(new Promise(() => {}));

    const wrapper = createWrapper();
    await nextTick();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.status.loading');
  });

  it('should show the desktop-only message outside Electron', async () => {
    mocks.isPackaged = false;

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.desktop_only');
    expect(mocks.getMcpServerStatus).not.toHaveBeenCalled();
  });

  it('should generate and display a bearer token in Docker', async () => {
    vi.stubEnv('VITE_DOCKER', 'true');
    mocks.isPackaged = false;

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.docker_description');
    expect(wrapper.find('code').text()).toBe(`${window.location.origin}/mcp`);
    expect(wrapper.text()).not.toContain('backend_settings.settings.mcp_server.desktop_only');

    await wrapper.find('[data-testid="mcp-generate-token"]').trigger('click');
    await flushPromises();

    expect(mocks.generateMcpToken).toHaveBeenCalledOnce();
    expect(wrapper.find('[data-testid="mcp-token"]').text()).toBe('••••••••••••••••');
    expect(wrapper.findAll('.copy-tooltip')[1].attributes('data-value')).toBe(
      'generated-mcp-token',
    );
    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.token_expiry_hint');

    await wrapper.find('[data-testid="mcp-toggle-token"]').trigger('click');
    expect(wrapper.find('[data-testid="mcp-token"]').text()).toBe('generated-mcp-token');
    expect(mocks.getMcpServerStatus).not.toHaveBeenCalled();
  });

  it('should show token generation errors separately in Docker', async () => {
    vi.stubEnv('VITE_DOCKER', 'true');
    mocks.isPackaged = false;
    mocks.generateMcpToken.mockRejectedValueOnce(new Error('token failed'));

    const wrapper = createWrapper();
    await wrapper.find('[data-testid="mcp-generate-token"]').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain(
      'backend_settings.settings.mcp_server.token_error',
    );
    expect(wrapper.text()).toContain('token failed');
    expect(wrapper.text()).not.toContain('backend_settings.settings.mcp_server.error');
  });
});
