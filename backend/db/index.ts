import { SQLDatabase } from "encore.dev/storage/sqldb";

export const db = new SQLDatabase("crypto_quant", {
  migrations: "./migrations",
});
