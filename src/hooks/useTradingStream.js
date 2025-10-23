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

    let socket;
    let reconnectTimeout;
    let shouldReconnect = true;

    const connect = () => {
      socket = new WebSocket(url);
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

      socket.addEventListener('close', () => {
        if (shouldReconnect) {
          reconnectTimeout = setTimeout(connect, 1500);
        }
      });
    };

    connect();

    return () => {
      shouldReconnect = false;
      if (socket) {
        socket.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, []);
};

export default useTradingStream;
