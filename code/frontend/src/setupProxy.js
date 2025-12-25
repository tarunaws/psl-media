// Proxy setup for local Flask backends
// Place this file in src/ as setupProxy.js

const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Specific highlight-trailer proxy FIRST so it doesn't get swallowed by generic /api
  app.use(
    '/api/highlight-trailer',
    createProxyMiddleware({
      target: 'http://localhost:5013',
      changeOrigin: true,
      pathRewrite: {
        '^/api/highlight-trailer': '/api/highlight-trailer',
      },
      logLevel: 'debug',
    })
  );
  // Shared visibility state service
  app.use(
    '/usecase-visibility',
    createProxyMiddleware({
      target: 'http://localhost:5012',
      changeOrigin: true,
      logLevel: 'debug',
    })
  );
  // Direct artifact streaming needs the original prefix to reach Flask route
  app.use(
    '/media-supply-chain/artifacts',
    createProxyMiddleware({
      target: 'http://localhost:5011',
      changeOrigin: true,
      // Express strips the mount path from req.url. The backend route is
      // `/media-supply-chain/artifacts/<path>`, so we need to prepend it back.
      pathRewrite: (path) => `/media-supply-chain/artifacts${path}`,
      logLevel: 'debug',
    })
  );
  // Media supply chain orchestrator service
  app.use(
    '/media-supply-chain',
    createProxyMiddleware({
      target: 'http://localhost:5011',
      changeOrigin: true,
      pathRewrite: {
        '^/media-supply-chain': '/',
      },
      logLevel: 'debug',
    })
  );
  // Generic API proxy (other services consolidated on 5011)
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:5011',
      changeOrigin: true,
      pathRewrite: {
        '^/api': '/api',
      },
      logLevel: 'debug',
    })
  );
};
