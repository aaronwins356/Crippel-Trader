const express = require('express');
const cors = require('cors');
const path = require('path');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'dist')));

// Proxy to LM Studio
app.use('/api/completion', createProxyMiddleware({
  target: 'http://localhost:1234',
  changeOrigin: true,
  pathRewrite: {
    '^/api/completion': '/v1/chat/completions'
  },
  onProxyReq: (proxyReq, req, res) => {
    // Add required headers for OpenAI API
    proxyReq.setHeader('Content-Type', 'application/json');
  }
}));

// Serve frontend
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Matrix LLM Chat running on http://localhost:${PORT}`);
  console.log('Ensure LM Studio is running on http://localhost:1234');
});