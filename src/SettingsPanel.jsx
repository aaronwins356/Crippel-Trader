import React from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

const TRADE_FREQUENCY_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
];

const riskMarks = [
  { value: 0, label: '0%' },
  { value: 0.25, label: '25%' },
  { value: 0.5, label: '50%' },
  { value: 0.75, label: '75%' },
  { value: 1, label: '100%' },
];

const SettingsPanel = ({
  settings,
  onFieldChange,
  onSubmit,
  disabled,
  saving,
}) => (
  <Card elevation={3} sx={{ borderRadius: 3 }}>
    <CardHeader
      title="Strategy Controls"
      subheader="Fine-tune the bot before deploying to the market"
    />
    <CardContent>
      <Stack spacing={4}>
        <Box>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Risk Appetite
          </Typography>
          <Typography variant="h4" fontWeight="bold" gutterBottom>
            {(Number(settings.risk) * 100).toFixed(0)}%
          </Typography>
          <Slider
            min={0}
            max={1}
            step={0.01}
            marks={riskMarks}
            value={Number(settings.risk) || 0}
            disabled={disabled}
            onChange={(_, value) => onFieldChange('risk', Array.isArray(value) ? value[0] : value)}
            valueLabelDisplay="auto"
            valueLabelFormat={(value) => `${Math.round(value * 100)}%`}
          />
        </Box>

        <FormControl fullWidth disabled={disabled}>
          <InputLabel id="trade-frequency-label">Trade Frequency</InputLabel>
          <Select
            labelId="trade-frequency-label"
            label="Trade Frequency"
            value={settings.trade_frequency || 'medium'}
            onChange={(event) => onFieldChange('trade_frequency', event.target.value)}
          >
            {TRADE_FREQUENCY_OPTIONS.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          label="Max Concurrent Positions"
          type="number"
          value={settings.max_positions ?? 1}
          onChange={(event) => onFieldChange('max_positions', Number(event.target.value))}
          fullWidth
          disabled={disabled}
          inputProps={{ min: 1, max: 100 }}
        />

        <Box display="flex" justifyContent="flex-end">
          <Button
            color="primary"
            variant="contained"
            onClick={onSubmit}
            disabled={disabled || saving}
            size="large"
          >
            {saving ? 'Saving…' : 'Save Settings'}
          </Button>
        </Box>
      </Stack>
    </CardContent>
  </Card>
);

SettingsPanel.propTypes = {
  settings: PropTypes.shape({
    risk: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
    trade_frequency: PropTypes.string.isRequired,
    max_positions: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  }).isRequired,
  onFieldChange: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  saving: PropTypes.bool,
};

SettingsPanel.defaultProps = {
  disabled: false,
  saving: false,
};

export default SettingsPanel;
