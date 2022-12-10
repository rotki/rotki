import { default as net } from 'node:net';

export const DEFAULT_PORT = 4242;

function checkAvailability(port: number): Promise<number> {
  return new Promise<number>((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(port, 'localhost', () => {
      const address = server.address();
      server.close();
      if (address && typeof address !== 'string') {
        resolve(address.port);
      } else {
        reject(new Error(`Invalid Address value ${address}`));
      }
    });
  });
}

export async function selectPort(
  startPort: number = DEFAULT_PORT
): Promise<number> {
  for (let portNumber = startPort; portNumber <= 65535; portNumber++) {
    try {
      return await checkAvailability(portNumber);
    } catch (e: any) {
      if (!['EADDRINUSE', 'EACCES'].includes(e.code)) {
        throw e;
      }
    }
  }
  throw new Error('no free ports found');
}
