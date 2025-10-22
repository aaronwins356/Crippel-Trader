import { useState, useEffect } from "react";
import backend from "~backend/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, TrendingUp, TrendingDown, Activity } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

export default function Overview() {
  const [assets, setAssets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const { toast } = useToast();

  const loadOverview = async () => {
    setLoading(true);
    try {
      const data = await backend.api.getAssetOverview();
      setAssets(data.assets);
    } catch (error) {
      console.error("Failed to load overview:", error);
      toast({
        title: "Error",
        description: "Failed to load market overview",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const syncMarketData = async () => {
    setSyncing(true);
    try {
      await backend.data_collection.syncMarketData({
        symbols: ["BTC", "ETH", "BNB", "SOL", "ADA", "XRP", "DOT", "AVAX"],
        interval: "1h",
        limit: 24
      });
      toast({
        title: "Success",
        description: "Market data synchronized",
      });
      await loadOverview();
    } catch (error) {
      console.error("Failed to sync market data:", error);
      toast({
        title: "Error",
        description: "Failed to sync market data",
        variant: "destructive",
      });
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    loadOverview();
    const interval = setInterval(loadOverview, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Activity className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground">Market Overview</h2>
          <p className="text-muted-foreground">Real-time cryptocurrency market data</p>
        </div>
        <Button onClick={syncMarketData} disabled={syncing}>
          <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
          {syncing ? "Syncing..." : "Sync Data"}
        </Button>
      </div>

      {assets.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">No market data available</p>
            <Button onClick={syncMarketData} disabled={syncing}>
              <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
              Sync Market Data
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {assets.map((asset: any) => (
            <Card key={asset.symbol} className="hover:shadow-lg transition-all hover:border-primary/50">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{asset.name}</CardTitle>
                  <span className="text-sm text-muted-foreground font-mono">
                    {asset.symbol}
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <div className="text-2xl font-bold text-foreground">
                      ${asset.currentPrice.toLocaleString(undefined, { 
                        minimumFractionDigits: 2, 
                        maximumFractionDigits: 2 
                      })}
                    </div>
                    <div className={`flex items-center gap-1 text-sm font-medium ${
                      asset.change24hPercent >= 0 ? "text-green-500" : "text-red-500"
                    }`}>
                      {asset.change24hPercent >= 0 ? (
                        <TrendingUp className="h-4 w-4" />
                      ) : (
                        <TrendingDown className="h-4 w-4" />
                      )}
                      {asset.change24hPercent >= 0 ? "+" : ""}
                      {asset.change24hPercent.toFixed(2)}%
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border">
                    <div>
                      <div className="text-xs text-muted-foreground">24h Change</div>
                      <div className="text-sm font-medium">
                        ${Math.abs(asset.change24h).toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">24h Volume</div>
                      <div className="text-sm font-medium">
                        ${(asset.volume24h / 1000000).toFixed(1)}M
                      </div>
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
