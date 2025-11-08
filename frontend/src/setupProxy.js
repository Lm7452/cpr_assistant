const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/ws', // This will proxy any request that starts with /ws
    createProxyMiddleware({
      target: 'http://localhost:8000', // Your Python server
      changeOrigin: true,
      ws: true, // This line is ESSENTIAL for WebSockets
    })
  );
};