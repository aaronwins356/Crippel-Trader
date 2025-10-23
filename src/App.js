import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  CssBaseline,
  Grid,
  Paper,
  Snackbar,
  Stack,
  Typography,
} from '@mui/material';
import SettingsPanel from './SettingsPanel.jsx';

const DEFAULT_SETTINGS = {
  risk: 0.2,
  trade_frequency: 'medium',
  max_positions: 5,
};

const STATUS_LABELS = {
  running: 'Running',
  paused: 'Paused',
  stopped: 'Stopped',
};

const App = () => {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [status, setStatus] = useState({ status: 'stopped', updated_at: new Date().toISOString() });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [error, setError] = useState(null);

  const notify = useCallback((message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
  }, []);

  const fetchJson = useCallback(async (input, init) => {
    const response = await fetch(input, init);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = data?.detail || data?.message || 'Unexpected server response';
      throw new Error(message);
    }
    return data;
  }, []);

  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);
      const [settingsResponse, statusResponse] = await Promise.all([
        fetchJson('/api/settings'),
        fetchJson('/api/status').catch(() => ({ status: 'stopped', updated_at: new Date().toISOString() })),
      ]);
      setSettings(settingsResponse ?? DEFAULT_SETTINGS);
      setStatus(statusResponse ?? { status: 'stopped', updated_at: new Date().toISOString() });
      setError(null);
    } catch (err) {
      console.error('Failed to load initial state', err);
      setError(err.message || 'Unable to load settings from the server.');
    } finally {
      setLoading(false);
    }
  }, [fetchJson]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  const handleFieldChange = useCallback((field, value) => {
    setSettings((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleSettingsSubmit = useCallback(async () => {
    try {
      setSaving(true);
      const payload = await fetchJson('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...settings,
          max_positions: Number(settings.max_positions),
          risk: Number(settings.risk),
        }),
      });
      setSettings(payload);
      notify('Settings saved successfully.');
    } catch (err) {
      console.error('Failed to update settings', err);
      notify(err.message || 'Unable to save settings.', 'error');
    } finally {
      setSaving(false);
    }
  }, [fetchJson, notify, settings]);

  const toggleStatus = useCallback(async () => {
    const nextStatus = status.status === 'running' ? 'stopped' : 'running';
    try {
      setStatusUpdating(true);
      const payload = await fetchJson('/api/status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus }),
      });
      setStatus(payload);
      notify(`Bot ${nextStatus === 'running' ? 'started' : 'stopped'} successfully.`);
    } catch (err) {
      console.error('Failed to toggle bot status', err);
      notify(err.message || 'Unable to toggle the bot.', 'error');
    } finally {
      setStatusUpdating(false);
    }
  }, [fetchJson, notify, status.status]);

  const statusMeta = useMemo(() => {
    try {
      return new Date(status.updated_at);
    } catch (e) {
      return new Date();
    }
  }, [status.updated_at]);

  return (
    <React.Fragment>
      <CssBaseline />
      <Box
        sx={{
          minHeight: '100vh',
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #312e81 100%)',
          py: 8,
          color: '#f8fafc',
        }}
      >
        <Container maxWidth="lg">
          <Stack spacing={4}>
            <Box>
              <Typography variant="overline" color="primary.light" sx={{ letterSpacing: 2 }}>
                Crippel Trader
              </Typography>
              <Typography variant="h3" fontWeight={700} gutterBottom>
                Trading Bot Control Tower
              </Typography>
              <Typography variant="subtitle1" color="rgba(241, 245, 249, 0.75)">
                Monitor the live status of your trading automation and refine strategy parameters
                without leaving this dashboard.
              </Typography>
            </Box>

            {error && (
              <Alert severity="error" variant="filled">
                {error}
              </Alert>
            )}

            {loading ? (
              <Box display="flex" justifyContent="center" py={10}>
                <CircularProgress color="inherit" thickness={4} />
              </Box>
            ) : (
              <Grid container spacing={4}>
                <Grid item xs={12} md={7}>
                  <SettingsPanel
                    settings={settings}
                    onFieldChange={handleFieldChange}
                    onSubmit={handleSettingsSubmit}
                    disabled={saving || statusUpdating}
                    saving={saving}
                  />
                </Grid>
                <Grid item xs={12} md={5}>
                  <Paper
                    elevation={6}
                    sx={{
                      borderRadius: 3,
                      background: 'rgba(15, 23, 42, 0.75)',
                      backdropFilter: 'blur(10px)',
                      color: '#f8fafc',
                      p: 4,
                    }}
                  >
                    <Stack spacing={3}>
                      <Box>
                        <Typography variant="subtitle2" color="rgba(241, 245, 249, 0.65)">
                          Bot Status
                        </Typography>
                        <Typography variant="h3" fontWeight={700} gutterBottom>
                          {STATUS_LABELS[status.status] || 'Unknown'}
                        </Typography>
                        <Typography variant="body2" color="rgba(241, 245, 249, 0.65)">
                          Last updated {statusMeta.toLocaleString()}
                        </Typography>
                      </Box>
                      <Stack direction="row" spacing={2}>
                        <Button
                          variant="contained"
                          color={status.status === 'running' ? 'secondary' : 'success'}
                          onClick={toggleStatus}
                          disabled={statusUpdating}
                          fullWidth
                          size="large"
                        >
                          {statusUpdating
                            ? 'Updating…'
                            : status.status === 'running'
                              ? 'Stop Bot'
                              : 'Start Bot'}
                        </Button>
                        <Button
                          variant="outlined"
                          color="inherit"
                          disabled={loading || saving || statusUpdating}
                          onClick={loadInitialData}
                          fullWidth
                          size="large"
                        >
                          Refresh
                        </Button>
                      </Stack>
                    </Stack>
                  </Paper>
                </Grid>
              </Grid>
            )}
          </Stack>
        </Container>
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          elevation={6}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </React.Fragment>
  );
};

export default App;
