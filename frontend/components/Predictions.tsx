import { useState } from "react";
import backend from "~backend/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Activity, TrendingUp } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

export default function Predictions() {
  const [symbol, setSymbol] = useState("BTC");
  const [predictions, setPredictions] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const loadPredictions = async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const data = await backend.analysis.getPredictions({ symbol, limit: 5 });
      setPredictions(data);
    } catch (error) {
      console.error("Failed to load predictions:", error);
      toast({
        title: "Error",
        description: "Failed to load predictions",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Price Predictions</h2>
        <p className="text-muted-foreground">AI-powered price forecasting with confidence intervals</p>
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
              <Button onClick={loadPredictions} disabled={loading}>
                <Activity className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                {loading ? "Loading..." : "Load Predictions"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {predictions && predictions.predictions && predictions.predictions.length > 0 && (
        <div className="space-y-4">
          {predictions.accuracy.mape !== null && (
            <Card>
              <CardHeader>
                <CardTitle>Model Accuracy</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">Mean Absolute Error</div>
                    <div className="text-2xl font-bold">{predictions.accuracy.mape?.toFixed(2)}%</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Model</div>
                    <div className="text-2xl font-bold">{predictions.predictions[0].modelName}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4">
            {predictions.predictions.map((pred: any, idx: number) => (
              <Card key={idx}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">
                      Target: {new Date(pred.targetTimestamp).toLocaleString()}
                    </CardTitle>
                    <span className="text-xs text-muted-foreground">
                      Predicted: {new Date(pred.predictionTimestamp).toLocaleString()}
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-3 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground mb-1">Predicted Price</div>
                      <div className="text-2xl font-bold text-primary">
                        ${pred.predictedPrice.toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground mb-1">Confidence Range (95%)</div>
                      <div className="text-sm">
                        <div className="text-green-500">${pred.confidenceUpper.toFixed(2)}</div>
                        <div className="text-red-500">${pred.confidenceLower.toFixed(2)}</div>
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground mb-1">Feature Importance</div>
                      <div className="space-y-1">
                        {Object.entries(pred.featureImportance || {}).slice(0, 3).map(([key, value]: [string, any]) => (
                          <div key={key} className="flex justify-between text-xs">
                            <span>{key.replace(/_/g, ' ')}</span>
                            <span className="font-mono">{(value * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
