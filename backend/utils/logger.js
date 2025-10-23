import dayjs from 'dayjs';

const format = (level, message, meta) => {
  const time = dayjs().format('YYYY-MM-DD HH:mm:ss.SSS');
  const base = `[CrippelTrader] [${level.toUpperCase()}] ${time} :: ${message}`;
  if (!meta) return base;
  if (meta instanceof Error) {
    return `${base}\n${meta.stack}`;
  }
  return `${base} ${JSON.stringify(meta)}`;
};

export const logger = {
  info(message, meta) {
    console.log(format('info', message, meta));
  },
  warn(message, meta) {
    console.warn(format('warn', message, meta));
  },
  error(message, meta) {
    console.error(format('error', message, meta));
  },
  debug(message, meta) {
    if (process.env.NODE_ENV === 'development') {
      console.debug(format('debug', message, meta));
    }
  }
};

export default logger;
