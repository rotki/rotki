import net from 'node:net';

export const DEFAULT_PORT = 4242;

export const DEFAULT_COLIBRI_PORT = 4343;

export const DEFAULT_MCP_PORT = 4445;

export const DEFAULT_PROXY_PORT = 4141;

async function checkAvailability(port: number, host: string): Promise<number> {
  return new Promise<number>((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(port, host, () => {
      const address = server.address();
      server.close();
      if (address && typeof address !== 'string')
        resolve(address.port);
      else reject(new Error(`Invalid Address value ${address}`));
    });
  });
}

/**
 * Whether a port can be bound right now. For callers that must have one exact
 * port rather than the next free one, so they can fail with their own message
 * instead of silently landing somewhere else.
 */
export async function isPortFree(port: number, host: string = 'localhost'): Promise<boolean> {
  try {
    await checkAvailability(port, host);
    return true;
  }
  catch (error: any) {
    if (['EADDRINUSE', 'EACCES'].includes(error.code))
      return false;
    throw error;
  }
}

export async function selectPort(startPort: number = DEFAULT_PORT, host: string = 'localhost'): Promise<number> {
  for (let portNumber = startPort; portNumber <= 65535; portNumber++) {
    try {
      return await checkAvailability(portNumber, host);
    }
    catch (error: any) {
      if (!['EADDRINUSE', 'EACCES'].includes(error.code))
        throw error;
    }
  }
  throw new Error('no free ports found');
}
