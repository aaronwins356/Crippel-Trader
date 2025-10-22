# Matrix LLM Chat

A Matrix-themed chat interface for your local LLM running in LM Studio. Experience chatting with AI in a futuristic terminal environment.

## Features

- Matrix code rain background animation
- Terminal-style chat interface with green text on black background
- Streaming responses from your local LLM with typing animation
- Fully responsive design
- Connection status indicator
- Boot sequence animation

## Prerequisites

1. [LM Studio](https://lmstudio.ai/) installed and running locally
2. A local LLM model loaded in LM Studio
3. Node.js (v14 or higher) installed

## Setup

1. Clone or download this repository

2. Install dependencies:
   ```bash
   npm install
   ```

3. Ensure LM Studio is running:
   - Open LM Studio
   - Load a model
   - Start the local server (default: http://localhost:1234)

## Usage

1. Start the application:
   ```bash
   npm start
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:3000
   ```

3. Wait for the boot sequence to complete

4. Type your message in the input field and press Enter or click SEND

5. Watch as the AI responds with a streaming typing animation

## How It Works

1. The frontend React app displays the Matrix-themed interface
2. The Node.js/Express backend serves the frontend and proxies requests to LM Studio
3. Messages are sent to LM Studio's OpenAI-compatible API endpoint
4. Responses are streamed back token-by-token for a real-time typing effect

## Customization

You can adjust the Matrix rain effect by modifying parameters in `src/MatrixRain.js`:
- `fontSize`: Size of characters
- `chars`: Characters used in the rain
- Animation speed in the `setInterval` call

## Troubleshooting

- If you get connection errors, ensure LM Studio is running on http://localhost:1234
- If the model doesn't respond, check that a model is loaded in LM Studio
- For performance issues, reduce the number of raindrops in `MatrixRain.js`

## Technologies Used

- Frontend: React, CSS3
- Backend: Node.js, Express
- Animations: Canvas API for Matrix effect
- Streaming: Fetch API with ReadableStream