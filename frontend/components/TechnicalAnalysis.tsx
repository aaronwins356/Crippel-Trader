import { useState } from "react";
import backend from "~backend/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus, Activity } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

export default function TechnicalAnalysis() {
  const [symbol, setSymbol] = useState("BTC");
  const [indicators, setIndicators] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const loadIndicators = async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const data = await backend.analysis.getIndicators({ symbol, interval: "1h" });
      setIndicators(data);
    } catch (error) {
      console.error("Failed to load indicators:", error);
      toast({
        title: "Error",
        description: "Failed to load technical indicators",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const getSignalBadge = (signal: string) => {
    if (signal === "bullish" || signal === "oversold") {
      return <Badge className="bg-green-500/20 text-green-500 border-green-500/50">{signal}</Badge>;
    } else if (signal === "bearish" || signal === "overbought") {
      return <Badge className="bg-red-500/20 text-red-500 border-red-500/50">{signal}</Badge>;
    }
    return <Badge variant="outline">{signal}</Badge>;
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Technical Analysis</h2>
        <p className="text-muted-foreground">Advanced technical indicators and signals</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Asset</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <Label htmlFor="symbol">Asset Symbol</Label>
              <Input
                id="symbol"
                value={symbol}
                onChange={(e: any) => setSymbol(e.target.value.toUpperCase())}
                placeholder="e.g., BTC, ETH"
              />
            </div>
            <div className="flex items-end">
              <Button onClick={loadIndicators} disabled={loading}>
                <Activity className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                {loading ? "Loading..." : "Analyze"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {indicators && indicators.current && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Market Signals for {indicators.symbol}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-muted-foreground mb-2">RSI Signal</div>
                  {getSignalBadge(indicators.signals.rsi)}
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-2">MACD Signal</div>
                  {getSignalBadge(indicators.signals.macd)}
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-2">Stochastic</div>
                  {getSignalBadge(indicators.signals.stochastic)}
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-2">Trend</div>
                  {getSignalBadge(indicators.signals.trend)}
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">RSI (14)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-foreground">
                  {indicators.current.rsi14.toFixed(2)}
                </div>
                <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${
                      indicators.current.rsi14 > 70 ? "bg-red-500" :
                      indicators.current.rsi14 < 30 ? "bg-green-500" :
                      "bg-primary"
                    }`}
                    style={{ width: `${indicators.current.rsi14}%` }}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">MACD</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">MACD</span>
                    <span className="text-sm font-mono">{indicators.current.macd.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Signal</span>
                    <span className="text-sm font-mono">{indicators.current.macdSignal.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Histogram</span>
                    <span className={`text-sm font-mono ${
                      indicators.current.macdHistogram >= 0 ? "text-green-500" : "text-red-500"
                    }`}>
                      {indicators.current.macdHistogram.toFixed(4)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Moving Averages</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">SMA 20</span>
                    <span className="text-sm font-mono">${indicators.current.sma20.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">SMA 50</span>
                    <span className="text-sm font-mono">${indicators.current.sma50.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">SMA 200</span>
                    <span className="text-sm font-mono">${indicators.current.sma200.toFixed(2)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Bollinger Bands</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Upper</span>
                    <span className="text-sm font-mono">${indicators.current.bollingerUpper.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Middle</span>
                    <span className="text-sm font-mono">${indicators.current.bollingerMiddle.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Lower</span>
                    <span className="text-sm font-mono">${indicators.current.bollingerLower.toFixed(2)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Stochastic</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">%K</span>
                    <span className="text-sm font-mono">{indicators.current.stochasticK.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">%D</span>
                    <span className="text-sm font-mono">{indicators.current.stochasticD.toFixed(2)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">ATR (14)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-foreground">
                  {indicators.current.atr.toFixed(2)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Average True Range
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
