# Crippel Trader

Crippel Trader is a self-contained trading laboratory that generates realistic multi-asset market data, drives an automated strategy, and streams the results into a polished web dashboard. It is ideal for demonstrations, education, and rapid experimentation—no brokerage or live capital required.

---

## Why you'll like it
- **Synthetic but lifelike data** – Continuous candles for crypto, equities, and macro assets with indicator overlays.
- **Automated strategy + manual control** – A systematic engine runs out of the box while still allowing manual order overrides.
- **Immersive dashboard** – React + WebSockets deliver a professional command-center view of market structure, risk, and execution.

---

## Before you begin (no coding experience needed)
1. **Install Node.js (version 18 or later)**
   - Visit [https://nodejs.org](https://nodejs.org) and download the "LTS" installer for your operating system.
   - Run the installer and accept the defaults. This also installs npm, the package manager we use below.
2. **Verify the installation**
   - Open *Terminal* (macOS/Linux) or *Command Prompt* (Windows).
   - Type `node -v` and press Enter. You should see a version number such as `v18.x.x`.
   - Type `npm -v` and press Enter. Any version number means npm is ready.

That is all you need. No databases, brokers, or extra services are required.

---

## Set up the project (about 10 minutes)
1. **Get the project files**
   - If you use Git: `git clone https://github.com/<your-org>/Crippel-Trader.git`
   - Alternatively, download the ZIP from your source control platform and unzip it to a convenient folder.
2. **Open the project folder in a terminal**
   - Example: `cd Crippel-Trader`
3. **Install the dependencies**
   - Run `npm install`
   - What happens: npm downloads all JavaScript libraries the app needs and stores them in the `node_modules` folder.
4. **Start the live simulation (development mode)**
   - Run `npm run dev`
   - This launches two processes:
     - the Express backend server on **http://localhost:4000**
     - the React development server on **http://localhost:3000**
   - Your browser should open automatically. If it does not, manually visit [http://localhost:3000](http://localhost:3000).
5. **Explore the dashboard**
   - Switch between assets, watch real-time charts, and review the portfolio and strategy logs as they stream in.

You can stop the simulation at any time by pressing `Ctrl + C` in the terminal window that is running the servers.

---

## Creating a production build (optional)
If you would like to deploy a compiled version of the app:
1. Ensure the development servers are stopped (`Ctrl + C`).
2. Run `npm run build` to compile the frontend into static files inside the `dist/` directory.
3. Run `npm start` to serve both the API and the precompiled frontend from the same Express server at **http://localhost:4000**.
4. Open [http://localhost:4000](http://localhost:4000) in your browser to access the bundled dashboard.

---

## Manual trading overrides (advanced users)
The automated strategy runs continuously, but you can post manual trades through the REST API. Here is a simple example using `curl` (available on macOS, Linux, and Windows 10+):

```bash
curl -X POST http://localhost:4000/api/orders \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC-USD","quantity":2,"price":41000}'
```

- `symbol` is the instrument ticker (see the dashboard for available choices).
- `quantity` is positive for buy orders and negative for sell orders.
- `price` is the limit price you are willing to trade at.

Each order is validated against the simulated portfolio, applied immediately, and reflected on the dashboard in real time.

---

## Troubleshooting tips
| Symptom | What to try |
| --- | --- |
| `npm install` fails with a permissions error | Re-run the command in a terminal that has write access to the project folder (on Windows, open **Command Prompt** as Administrator). |
| Browser shows a blank page | Ensure both `npm run dev` processes are running. Check the terminal for errors and restart the command. |
| Port already in use | Close other applications using ports 3000 or 4000, then run the command again. |
| Need to reset data | Stop the servers, delete the `node_modules` folder, run `npm install`, and start again. |

---

## Project structure at a glance
```
backend/
  data/seedAssets.js         # Instrument universe
  services/                  # Market generator, portfolio engine, strategy
  utils/                     # Technical indicator calculations
src/
  components/                # React UI building blocks
  hooks/useTradingStream.js  # WebSocket abstraction
  utils/format.js            # Formatting helpers
  App.js                     # Dashboard layout
  index.js / index.html      # Entry point
  styles.css                 # Theme
```

---

## Disclaimer
Crippel Trader is a fully synthetic environment designed for demonstration and educational purposes. It **does not** connect to live markets nor execute real trades.
