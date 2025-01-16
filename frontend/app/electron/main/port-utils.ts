import net from 'node:net';
import { assert } from '@rotki/common';

export const DEFAULT_PORT = 4242;

export const DEFAULT_COLIBRI_PORT = 4343;

async function checkAvailability(port: number): Promise<number> {
  return new Promise<number>((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(port, 'localhost', () => {
      const address = server.address();
      server.close();
      if (address && typeof address !== 'string')
        resolve(address.port);
      else reject(new Error(`Invalid Address value ${address}`));
    });
  });
}

export async function selectPort(startPort: number = DEFAULT_PORT): Promise<number> {
  for (let portNumber = startPort; portNumber <= 65535; portNumber++) {
    try {
      return await checkAvailability(portNumber);
    }
    catch (error: any) {
      if (!['EADDRINUSE', 'EACCES'].includes(error.code))
        throw error;
    }
  }
  throw new Error('no free ports found');
}

export async function getPortAndUrl(defaultPort: number, apiUrl: string): Promise<[number, string, boolean]> {
  const port = await selectPort(defaultPort);

  const regExp = /(.*):\/\/(.*):(.*)/;
  const match = apiUrl.match(regExp);
  assert(match && match.length === 4);
  const [, scheme, host, oldPort] = match;
  assert(host);

  return [
    port,
    `${scheme}://${host}:${port}`,
    port !== defaultPort && Number.parseInt(oldPort) !== port,
  ];
}
