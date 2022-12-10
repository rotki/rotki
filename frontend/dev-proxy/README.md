# rotki development proxy

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

> The premium components directory is needed only if you need to test the premium components themselves. 
> Assuming that the premium-components repo is at the same parent folder as the application repository one would
> have to add the following in the `.env` file.
> 
> `PREMIUM_COMPONENT_DIR=/home/user/path/premium-components/packages/premium-components`


You can provide this configuration in a `.env` file in the `dev-proxy` directory.

## Starting the proxy

From the parent directory

```bash
pnpm install
pnpm run --filter @rotki/dev-proxy serve
```

## Setup rotki

In order to use rotki with this development proxy you need to create a `.env.development.local`
environment file. Put the file in the frontend directory of rotki. (`frontend/app`).

The file must contain the following entry:

```env
VITE_BACKEND_URL=http://localhost:4243
```

> Adjust accordingly to if you used a custom port for the proxy.

After that you can start rotki via:

```bash
pnpm run dev
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
npm ci
npm run build
```

## Mocking async queries

Look into the `async-mock.example.json` and create an `async-mock.json` file in the same 
directory. Follow a similar structure as the example.

```json 
{
  "/api/1/assets/updates": {
    "GET": [
      {
        "result": {
          "local_version": 1,
          "remote_version": 6
        },
        "message": ""
      },
      {
        "result": {
          "local_version": 2,
          "remote_version": 5
        },
        "message": ""
      }
    ]
  }
}
```

You can put the mocked url on the root of the json and under that you can add the request
verb. The request verb can either be an object or an array.

If an object is used, this object will be returned every time you query the same endpoint/verb combination.
If an array is used instead for each request the next index available will be served. e.g. The first request
will serve the item at index `0`, the second the item and index `1` etc. If the end of the available responses 
is reached the last item will keep being returned for any consequent requests.
