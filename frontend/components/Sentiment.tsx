import { useState } from "react";
import backend from "~backend/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Activity, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

export default function Sentiment() {
  const [symbol, setSymbol] = useState("BTC");
  const [sentiment, setSentiment] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const loadSentiment = async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const data = await backend.data_collection.getSentiment({ symbol, days: 7 });
      setSentiment(data);
    } catch (error) {
      console.error("Failed to load sentiment:", error);
      toast({
        title: "Error",
        description: "Failed to load sentiment data",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.3) return "text-green-500";
    if (score < -0.3) return "text-red-500";
    return "text-muted-foreground";
  };

  const getTrendIcon = (trend: string) => {
    if (trend === "improving") return <TrendingUp className="h-4 w-4 text-green-500" />;
    if (trend === "declining") return <TrendingDown className="h-4 w-4 text-red-500" />;
    return <Minus className="h-4 w-4 text-muted-foreground" />;
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Sentiment Analysis</h2>
        <p className="text-muted-foreground">Market sentiment from news and social media</p>
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
              <Button onClick={loadSentiment} disabled={loading}>
                <Activity className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                {loading ? "Loading..." : "Analyze"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {sentiment && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Current Sentiment for {sentiment.symbol}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-6">
                <div>
                  <div className="text-sm text-muted-foreground mb-2">Sentiment Score</div>
                  <div className={`text-4xl font-bold ${getSentimentColor(sentiment.currentSentiment)}`}>
                    {sentiment.currentSentiment.toFixed(2)}
                  </div>
                  <div className="mt-2 h-3 bg-muted rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${
                        sentiment.currentSentiment > 0 ? "bg-green-500" : "bg-red-500"
                      }`}
                      style={{ 
                        width: `${Math.abs(sentiment.currentSentiment) * 50 + 50}%`,
                        marginLeft: sentiment.currentSentiment < 0 ? `${50 - Math.abs(sentiment.currentSentiment) * 50}%` : '0'
                      }}
                    />
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-2">Trend</div>
                  <div className="flex items-center gap-2">
                    {getTrendIcon(sentiment.trend)}
                    <span className="text-2xl font-bold capitalize">{sentiment.trend}</span>
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-2">Data Points</div>
                  <div className="text-2xl font-bold">{sentiment.data.length}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {sentiment.data.length > 0 && sentiment.data[sentiment.data.length - 1].topKeywords && (
            <Card>
              <CardHeader>
                <CardTitle>Trending Keywords</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {sentiment.data[sentiment.data.length - 1].topKeywords.slice(0, 15).map((keyword: string) => (
                    <Badge key={keyword} variant="secondary">{keyword}</Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4">
            {sentiment.data.slice().reverse().slice(0, 5).map((point: any, idx: number) => (
              <Card key={idx}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm text-muted-foreground">
                        {new Date(point.timestamp).toLocaleString()}
                      </div>
                      <div className={`text-2xl font-bold ${getSentimentColor(point.sentimentScore)}`}>
                        {point.sentimentScore.toFixed(2)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="flex gap-2 mb-2">
                        <Badge className="bg-green-500/20 text-green-500 border-green-500/50">
                          {point.positiveCount} positive
                        </Badge>
                        <Badge className="bg-red-500/20 text-red-500 border-red-500/50">
                          {point.negativeCount} negative
                        </Badge>
                        <Badge variant="outline">{point.neutralCount} neutral</Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {point.volumeMentions} mentions
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
