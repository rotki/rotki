# Rotki development proxy

The proxy's purpose is to provide an easy way to develop the frontend in parallel
with the backend, and provide an easy way to test the premium features.

The proxy will automatically pass any requests to the real backend, unless a mocked
endpoint implementation exists.

All mock endpoint implementations should be before:

```TypeScript
server.use(createProxyMiddleware({ target: backend }));
```

Otherwise the real backend will handle the requests.

## Configuration

You can configure the proxy, with the following environment variables:

- `PORT` The port where the proxy listens for incoming connections. (Default: 4243)
- `BACKEND` The url of the real backend. (Default: `http://localhost:4242`)
- `PREMIUM_COMPONENT_DIR` The premium components directory. (Optional)

You can provide this configuration in a `.env` file in the `dev-proxy` directory.

## Starting the proxy

After entering the directory you have to run the following commands:

```bash
npm ci
npm run serve
```

## Setup Rotki

In order to use rotki with this development proxy you need to create a `.env.development.local`
environment file. Put the file in the frontend directory of rotki. (`frontend/app`).

The file must contain the following entry:

```env
VUE_APP_BACKEND_URL=http://localhost:4243
```

> Adjust accordingly to if you used a custom port for the proxy.

After that you can start rotki via:

```bash
npm run electron:serve
```

## Serving the premium components

To serve the premium components using the proxy, you must the `PREMIUM_COMPONENT_DIR`
environment variable. The variable should contain the directory where you store your
premium components source code. You must have the variable set before starting the
proxy, otherwise the proxy will serve the production components instead.

Before accessing the premium components via the proxy, you must first build the bundle.
In order to build the bundle you need to go to the premium components directory and
run the following.

```bash
yarn build:bundle
```
