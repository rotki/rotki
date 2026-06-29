import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import McpServerCommand from '@/modules/settings/backend/McpServerCommand.vue';

const { mcpServerInfoMock } = vi.hoisted(() => ({
  mcpServerInfoMock: vi.fn(),
}));

vi.mock('@/modules/settings/api/use-settings-api', (): Record<string, unknown> => ({
  useSettingsApi: vi.fn().mockReturnValue({
    mcpServerInfo: mcpServerInfoMock,
  }),
}));

describe('mcpServerCommand', () => {
  function createWrapper(): VueWrapper<InstanceType<typeof McpServerCommand>> {
    return mount(McpServerCommand, {
      global: {
        stubs: {
          CopyTooltip: {
            props: {
              value: { type: String, required: true },
            },
            template: '<div class="copy-tooltip" :data-value="value"><slot /><slot name="label" /></div>',
          },
          RuiAlert: {
            props: {
              type: { type: String, required: true },
            },
            template: '<div class="rui-alert" :data-type="type"><slot /></div>',
          },
          RuiButton: {
            template: '<button><slot /></button>',
          },
          RuiIcon: {
            template: '<span />',
          },
          SettingsItem: {
            template: '<section><slot name="title" /><slot name="subtitle" /><slot /></section>',
          },
        },
      },
    });
  }

  beforeEach((): void => {
    mcpServerInfoMock.mockReset();
  });

  it('should show the MCP command when available', async () => {
    const displayCommand = '/usr/bin/python -m rotkehlchen mcp --backend-url http://127.0.0.1:5042/api/1';
    mcpServerInfoMock.mockResolvedValue({
      args: ['-m', 'rotkehlchen', 'mcp', '--backend-url', 'http://127.0.0.1:5042/api/1'],
      available: true,
      command: '/usr/bin/python',
      displayCommand,
    });

    const wrapper = createWrapper();
    await flushPromises();

    expect(mcpServerInfoMock).toHaveBeenCalledOnce();
    expect(wrapper.find('code').text()).toBe(displayCommand);
    expect(wrapper.find('.copy-tooltip').attributes('data-value')).toBe(displayCommand);
  });

  it('should show loading while the MCP command is loading', async () => {
    let resolveInfo!: (value: { available: false; reason: string }) => void;
    mcpServerInfoMock.mockReturnValue(new Promise(resolve => resolveInfo = resolve));

    const wrapper = createWrapper();
    await nextTick();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_command.loading');

    resolveInfo({ available: false, reason: 'not installed' });
    await flushPromises();
  });

  it('should show why MCP is unavailable', async () => {
    mcpServerInfoMock.mockResolvedValue({
      available: false,
      reason: 'MCP server command is unavailable because the optional mcp dependency is not installed.',
    });

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('.rui-alert').attributes('data-type')).toBe('info');
    expect(wrapper.text()).toContain('backend_settings.settings.mcp_command.unavailable');
    expect(wrapper.text()).toContain('optional mcp dependency is not installed');
  });

  it('should show an error when loading MCP information fails', async () => {
    mcpServerInfoMock.mockRejectedValue(new Error('backend unavailable'));

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('.rui-alert').attributes('data-type')).toBe('error');
    expect(wrapper.text()).toContain('backend unavailable');
  });
});
