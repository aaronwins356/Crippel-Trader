import { useState } from "react";
import backend from "~backend/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Activity } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

export default function OnChain() {
  const [symbol, setSymbol] = useState("BTC");
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const loadMetrics = async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const data = await backend.data_collection.getOnChainMetrics({ symbol, limit: 10 });
      setMetrics(data);
    } catch (error) {
      console.error("Failed to load on-chain metrics:", error);
      toast({
        title: "Error",
        description: "Failed to load on-chain metrics",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">On-Chain Metrics</h2>
        <p className="text-muted-foreground">Blockchain activity and whale movements</p>
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
              <Button onClick={loadMetrics} disabled={loading}>
                <Activity className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                {loading ? "Loading..." : "Load Metrics"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {metrics && metrics.metrics && metrics.metrics.length > 0 && (
        <div className="space-y-4">
          {metrics.metrics.slice().reverse().slice(0, 5).map((metric: any, idx: number) => (
            <Card key={idx}>
              <CardHeader>
                <CardTitle className="text-base">
                  {new Date(metric.timestamp).toLocaleString()}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Active Addresses</div>
                    <div className="text-lg font-bold">
                      {metric.activeAddresses ? metric.activeAddresses.toLocaleString() : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Transactions</div>
                    <div className="text-lg font-bold">
                      {metric.transactionCount ? metric.transactionCount.toLocaleString() : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Exchange Inflow</div>
                    <div className="text-lg font-bold text-red-500">
                      {metric.exchangeInflow ? `${(metric.exchangeInflow / 1000).toFixed(1)}K` : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Exchange Outflow</div>
                    <div className="text-lg font-bold text-green-500">
                      {metric.exchangeOutflow ? `${(metric.exchangeOutflow / 1000).toFixed(1)}K` : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Whale Transactions</div>
                    <div className="text-lg font-bold">
                      {metric.whaleTransactions || 0}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
