import net from 'node:net';

export const DEFAULT_PORT = 4242;

export const DEFAULT_COLIBRI_PORT = 4343;

export const DEFAULT_MCP_PORT = 4445;

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
