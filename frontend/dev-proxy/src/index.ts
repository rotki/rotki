import fs from 'fs';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { default as jsonServer } from 'json-server';
import { statistics } from '@/mocked-apis/statistics';
import { enableCors } from '@/setup';

const server = jsonServer.create();
const router = jsonServer.router('db.json');
const middlewares = jsonServer.defaults();

const port = process.env.PORT || 4243;
const backend = process.env.BACKEND || 'http://localhost:4242';
const componentsDir = process.env.PREMIUM_COMPONENT_DIR;

enableCors(server);

if (
  componentsDir &&
  fs.existsSync(componentsDir) &&
  fs.statSync(componentsDir).isDirectory()
) {
  console.info('Enabling statistics renderer support');
  statistics(server, componentsDir);
} else {
  console.warn(
    'PREMIUM_COMPONENT_DIR was not a valid directory, disabling statistics renderer support.'
  );
}

server.use(createProxyMiddleware({ target: backend }));
server.use(middlewares);
server.use(router);

server.listen(port, () => {
  console.log(`Proxy server is running at http://localhost:${port}`);
});
