// Proxy setup for local Flask backends
// Place this file in src/ as setupProxy.js

const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Highlight & Trailer service (5013)
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
};
