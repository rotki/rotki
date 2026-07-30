import { api } from '@/modules/core/api/rotki-api';
import { type McpToken, McpTokenSchema } from '@/modules/settings/types/mcp';

interface UseMcpApiReturn {
  generateMcpToken: () => Promise<McpToken>;
}

export function useMcpApi(): UseMcpApiReturn {
  const generateMcpToken = async (): Promise<McpToken> => {
    const response = await api.post<McpToken>('/mcp/token');
    return McpTokenSchema.parse(response);
  };

  return {
    generateMcpToken,
  };
}
