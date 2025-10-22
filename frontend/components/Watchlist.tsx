import { useState, useEffect } from "react";
import backend from "~backend/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Trash2, TrendingUp, TrendingDown } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

export default function Watchlist() {
  const [items, setItems] = useState<any[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [assetId, setAssetId] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const loadWatchlist = async () => {
    setLoading(true);
    try {
      const data = await backend.api.getWatchlist();
      setItems(data.items);
    } catch (error) {
      console.error("Failed to load watchlist:", error);
      toast({
        title: "Error",
        description: "Failed to load watchlist",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const addToWatchlist = async (e: any) => {
    e.preventDefault();
    try {
      await backend.api.addToWatchlist({ assetId: assetId.toLowerCase(), notes });
      toast({
        title: "Success",
        description: "Asset added to watchlist",
      });
      setAssetId("");
      setNotes("");
      setDialogOpen(false);
      await loadWatchlist();
    } catch (error) {
      console.error("Failed to add to watchlist:", error);
      toast({
        title: "Error",
        description: "Failed to add to watchlist",
        variant: "destructive",
      });
    }
  };

  const removeFromWatchlist = async (id: number) => {
    try {
      await backend.api.removeFromWatchlist({ id });
      toast({
        title: "Success",
        description: "Asset removed from watchlist",
      });
      await loadWatchlist();
    } catch (error) {
      console.error("Failed to remove from watchlist:", error);
      toast({
        title: "Error",
        description: "Failed to remove from watchlist",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    loadWatchlist();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Watchlist</h2>
          <p className="text-muted-foreground">Track your favorite assets</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add Asset
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add to Watchlist</DialogTitle>
            </DialogHeader>
            <form onSubmit={addToWatchlist} className="space-y-4">
              <div>
                <Label htmlFor="assetId">Asset ID</Label>
                <Input
                  id="assetId"
                  value={assetId}
                  onChange={(e: any) => setAssetId(e.target.value)}
                  placeholder="e.g., btc, eth"
                  required
                />
              </div>
              <div>
                <Label htmlFor="notes">Notes (optional)</Label>
                <Input
                  id="notes"
                  value={notes}
                  onChange={(e: any) => setNotes(e.target.value)}
                  placeholder="Add notes"
                />
              </div>
              <Button type="submit" className="w-full">Add</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Your watchlist is empty</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {items.map((item: any) => (
            <Card key={item.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{item.name}</CardTitle>
                  <Button variant="ghost" size="icon" onClick={() => removeFromWatchlist(item.id)}>
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {item.currentPrice && (
                    <div>
                      <div className="text-2xl font-bold">${item.currentPrice.toFixed(2)}</div>
                      {item.change24h && (
                        <div className={`flex items-center gap-1 text-sm ${
                          item.change24h >= 0 ? "text-green-500" : "text-red-500"
                        }`}>
                          {item.change24h >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                          ${Math.abs(item.change24h).toFixed(2)}
                        </div>
                      )}
                    </div>
                  )}
                  {item.notes && (
                    <p className="text-sm text-muted-foreground pt-2 border-t">{item.notes}</p>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
