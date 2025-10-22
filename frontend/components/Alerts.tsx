import { useState, useEffect } from "react";
import backend from "~backend/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Bell, Check, AlertTriangle } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

export default function Alerts() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const data = await backend.api.getAlerts({ limit: 20 });
      setAlerts(data.alerts);
    } catch (error) {
      console.error("Failed to load alerts:", error);
      toast({
        title: "Error",
        description: "Failed to load alerts",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const acknowledgeAlert = async (id: number) => {
    try {
      await backend.api.acknowledgeAlert({ id });
      toast({
        title: "Success",
        description: "Alert acknowledged",
      });
      await loadAlerts();
    } catch (error) {
      console.error("Failed to acknowledge alert:", error);
      toast({
        title: "Error",
        description: "Failed to acknowledge alert",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    loadAlerts();
    const interval = setInterval(loadAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityBadge = (severity: string) => {
    if (severity === "critical") {
      return <Badge className="bg-red-500/20 text-red-500 border-red-500/50">Critical</Badge>;
    } else if (severity === "warning") {
      return <Badge className="bg-yellow-500/20 text-yellow-500 border-yellow-500/50">Warning</Badge>;
    }
    return <Badge variant="outline">Info</Badge>;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Alerts & Events</h2>
          <p className="text-muted-foreground">Real-time market anomalies and notifications</p>
        </div>
        <Button onClick={loadAlerts}>
          <Bell className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {alerts.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">No alerts at this time</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert: any) => (
            <Card key={alert.id} className={alert.acknowledged ? "opacity-60" : ""}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CardTitle className="text-base">{alert.title}</CardTitle>
                    {getSeverityBadge(alert.severity)}
                    <Badge variant="secondary">{alert.assetId.toUpperCase()}</Badge>
                  </div>
                  {!alert.acknowledged && (
                    <Button 
                      size="sm" 
                      variant="outline" 
                      onClick={() => acknowledgeAlert(alert.id)}
                    >
                      <Check className="mr-2 h-4 w-4" />
                      Acknowledge
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-2">{alert.description}</p>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span>{new Date(alert.triggeredAt).toLocaleString()}</span>
                  <span>Type: {alert.alertType}</span>
                  {alert.acknowledged && (
                    <span>Acknowledged: {new Date(alert.acknowledgedAt).toLocaleString()}</span>
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
