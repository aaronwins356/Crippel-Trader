import { useEffect, useRef } from 'react';

const resolveSocketUrl = () => {
  if (typeof window === 'undefined') return '';
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host.includes('localhost')
    ? 'localhost:4000'
    : window.location.host;
  return `${protocol}//${host}/ws/stream`;
};

const useTradingStream = (onPayload) => {
  const handlerRef = useRef(onPayload);

  useEffect(() => {
    handlerRef.current = onPayload;
  }, [onPayload]);

  useEffect(() => {
    const url = resolveSocketUrl();
    if (!url) return () => {};

    const socket = new WebSocket(url);
    socket.addEventListener('message', (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (handlerRef.current) {
          handlerRef.current(payload);
        }
      } catch (error) {
        console.error('Failed to parse message', error);
      }
    });

    socket.addEventListener('error', (error) => {
      console.error('WebSocket error', error);
    });

    return () => {
      socket.close();
    };
  }, []);
};

export default useTradingStream;
