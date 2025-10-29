const DEFAULT_BASE_URL = 'http://127.0.0.1:1234';
const SYSTEM_PROMPT = 'You are a Python trading bot engineer.';
const DEFAULT_MODEL = 'qwen/qwen3-coder-30b';

function normaliseBaseUrl(baseUrl) {
  const trimmed = (baseUrl || DEFAULT_BASE_URL).trim();
  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed;
}

export async function sendChatCompletion({
  baseUrl = DEFAULT_BASE_URL,
  model = DEFAULT_MODEL,
  messages,
  temperature = 0.2,
}) {
  if (!Array.isArray(messages) || messages.length === 0) {
    throw new Error('Chat history must contain at least one user message.');
  }

  const target = `${normaliseBaseUrl(baseUrl)}/v1/chat/completions`;
  const payload = {
    model,
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      ...messages,
    ],
    temperature,
  };

  const response = await fetch(target, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`LLM request failed: ${response.status} ${detail}`);
  }

  const data = await response.json();
  const content = data?.choices?.[0]?.message?.content;
  if (!content) {
    throw new Error('LLM response did not contain any content.');
  }

  return content;
}

export { SYSTEM_PROMPT, DEFAULT_MODEL, DEFAULT_BASE_URL };
