import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Overview from "./components/Overview";
import TechnicalAnalysis from "./components/TechnicalAnalysis";
import Predictions from "./components/Predictions";
import Sentiment from "./components/Sentiment";
import OnChain from "./components/OnChain";
import Alerts from "./components/Alerts";
import Watchlist from "./components/Watchlist";
import { TrendingUp } from "lucide-react";

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="dark min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <TrendingUp className="h-7 w-7 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">
                  Crypto Quant Analyzer
                </h1>
                <p className="text-sm text-muted-foreground">
                  Professional-grade research & analysis platform
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-7 mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="technical">Technical</TabsTrigger>
            <TabsTrigger value="predictions">Predictions</TabsTrigger>
            <TabsTrigger value="sentiment">Sentiment</TabsTrigger>
            <TabsTrigger value="onchain">On-Chain</TabsTrigger>
            <TabsTrigger value="alerts">Alerts</TabsTrigger>
            <TabsTrigger value="watchlist">Watchlist</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <Overview />
          </TabsContent>

          <TabsContent value="technical" className="space-y-4">
            <TechnicalAnalysis />
          </TabsContent>

          <TabsContent value="predictions" className="space-y-4">
            <Predictions />
          </TabsContent>

          <TabsContent value="sentiment" className="space-y-4">
            <Sentiment />
          </TabsContent>

          <TabsContent value="onchain" className="space-y-4">
            <OnChain />
          </TabsContent>

          <TabsContent value="alerts" className="space-y-4">
            <Alerts />
          </TabsContent>

          <TabsContent value="watchlist" className="space-y-4">
            <Watchlist />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
