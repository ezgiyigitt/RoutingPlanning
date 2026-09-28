import { useEffect, useState } from "react";
import { AppContextType } from "../App";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { Battery, BatteryFull, BatteryMedium, BatteryLow, CloudRain, Sun, Cloud, Snowflake, CarFront, Zap, Loader2, User, UserPlus } from "lucide-react";
import { getLocations } from "@/lib/api";

export default function StepPlanning({ state, setState, nextStep }: AppContextType) {
  const [locations, setLocations] = useState<string[]>([]);
  const [loadingLocs, setLoadingLocs] = useState(true);
  const [drivers, setDrivers] = useState<any[]>([]);
  const [showDriverModal, setShowDriverModal] = useState(false);
  const [newDriverName, setNewDriverName] = useState("");
  const newDriver = { isim: newDriverName, yas: 30, stres_egilimi: 0.5, yorgunluk_esigi: 60 };
  const setNewDriver = (driver: typeof newDriver) => setNewDriverName(driver.isim);

  useEffect(() => {
    fetch("http://localhost:8000/api/drivers")
      .then(res => res.json())
      .then(data => { if (data.drivers) setDrivers(data.drivers); })
      .catch(() => {});
  }, []);

  const handleAddDriver = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/drivers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          isim: newDriverName.trim(),
          yas: 30,
          stres_egilimi: 0.5,
          yorgunluk_esigi: 60,
        })
      });
      const data = await res.json();
      if(data.status === "ok") {
        setDrivers([...drivers, data.driver]);
        setState({ ...state, driverId: data.driver.uid });
        setNewDriverName("");
        setShowDriverModal(false);
      }
    } catch(e) {}
  };

  // Fetch Ankara locations from API
  useEffect(() => {
    getLocations()
      .then(locs => setLocations(locs))
      .catch(() => {
        // Fallback locations
        setLocations([
          "Altındağ", "Ayrancı", "Balgat", "Batıkent", "Bilkent",
          "Çankaya", "Çayyolu", "Dikmen", "Esenboğa", "Etimesgut",
          "Etlik", "Gölbaşı", "Hacettepe", "Kazan", "Kavaklıdere",
          "Keçiören", "Kızılay", "Konutkent", "Küçükesat", "Mamak",
          "ODTÜ", "Ostim", "Polatlı", "Pursaklar", "Sincan",
          "Söğütözü", "Şentepe", "TBMM", "Tunalı Hilmi", "Ulus",
          "Ümitköy", "Yaşamkent", "Yenimahalle",
        ]);
      })
      .finally(() => setLoadingLocs(false));
  }, []);

  const getBatteryIcon = (level: number) => {
    if (level > 80) return <BatteryFull className="w-5 h-5 text-green-500" />;
    if (level > 30) return <BatteryMedium className="w-5 h-5 text-primary" />;
    if (level > 10) return <BatteryLow className="w-5 h-5 text-orange-500" />;
    return <Battery className="w-5 h-5 text-destructive" />;
  };

  const getWeatherIcon = (weather: string) => {
    switch (weather) {
      case "Sunny": return <Sun className="w-4 h-4 mr-2" />;
      case "Cloudy": return <Cloud className="w-4 h-4 mr-2" />;
      case "Rainy": return <CloudRain className="w-4 h-4 mr-2" />;
      case "Snowy": return <Snowflake className="w-4 h-4 mr-2" />;
      default: return <Sun className="w-4 h-4 mr-2" />;
    }
  };

  const isFormValid = state.origin && state.destination && state.origin !== state.destination;
  const selectedDriver = drivers.find(d => d.uid === state.driverId);

  return (
    <div className="bg-card p-8 rounded-2xl shadow-sm border border-border/50">
      <div className="text-center mb-8 flex flex-col items-center gap-3">
        <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center animate-pulse">
          <Zap className="w-6 h-6 text-primary" />
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">AffectEV</h1>
        <p className="text-muted-foreground font-medium">Emotion-Aware Route Intelligence</p>
      </div>

      <div className="space-y-6">
        <div className="flex gap-2 items-end">
          <div className="flex-1 space-y-2">
            <Label>Driver Profile (Q-Learning)</Label>
            <Select value={state.driverId} onValueChange={(val) => setState({ ...state, driverId: val })}>
              <SelectTrigger>
                <div className="flex items-center">
                  <User className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Select Driver" />
                </div>
              </SelectTrigger>
              <SelectContent className="max-h-[300px] overflow-y-auto">
                {drivers.length > 0 ? drivers.map(d => (
                  <SelectItem key={d.uid} value={d.uid}>{d.isim} ({d.uid})</SelectItem>
                )) : (
                  <SelectItem value="U01">Loading...</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" onClick={() => setShowDriverModal(true)} className="h-10 px-3">
            <UserPlus className="w-4 h-4" />
          </Button>
        </div>

        {false && selectedDriver && (
          <div className="bg-primary/5 p-3 rounded-lg flex items-center justify-between text-sm border border-primary/20">
            <div>
              <span className="font-medium text-foreground">Profile Traits: </span>
              <span className="text-muted-foreground ml-1">
                Age: {selectedDriver.yas} • 
                Stress Tendency: {selectedDriver.stres_egilimi} • 
                Fatigue Threshold: {selectedDriver.yorgunluk_esigi}
              </span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <Label>Origin</Label>
            {loadingLocs ? (
              <div className="flex items-center space-x-2 h-10 px-3 border border-border rounded-lg text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Loading locations...</span>
              </div>
            ) : (
              <Select value={state.origin} onValueChange={(val) => setState({ ...state, origin: val })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select origin" />
                </SelectTrigger>
                <SelectContent className="max-h-[300px] overflow-y-auto">
                  {locations.map(d => (
                    <SelectItem key={`orig-${d}`} value={d}>{d}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div className="space-y-2">
            <Label>Destination</Label>
            {loadingLocs ? (
              <div className="flex items-center space-x-2 h-10 px-3 border border-border rounded-lg text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Loading locations...</span>
              </div>
            ) : (
              <Select value={state.destination} onValueChange={(val) => setState({ ...state, destination: val })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select destination" />
                </SelectTrigger>
                <SelectContent className="max-h-[300px] overflow-y-auto">
                  {locations.map(d => (
                    <SelectItem key={`dest-${d}`} value={d}>{d}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>

        {state.origin && state.destination && state.origin === state.destination && (
          <p className="text-sm text-destructive">⚠️ Origin and destination must be different</p>
        )}

        <div className="space-y-4 pt-2">
          <div className="flex justify-between items-center">
            <Label>Current Battery Level</Label>
            <div className="flex items-center space-x-2 font-medium">
              {getBatteryIcon(state.battery)}
              <span>{state.battery}%</span>
            </div>
          </div>
          <Slider
            value={[state.battery]}
            onValueChange={([val]) => setState({ ...state, battery: val })}
            min={20} max={80} step={1}
            className="py-2"
          />
          <p className="text-xs text-muted-foreground">Battery range: 20% – 80% (optimal for battery health)</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          <div className="space-y-2">
            <Label>Weather</Label>
            <Select value={state.weather} onValueChange={(val) => setState({ ...state, weather: val })}>
              <SelectTrigger>
                <div className="flex items-center">
                  {getWeatherIcon(state.weather)}
                  <SelectValue placeholder="Weather" />
                </div>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Sunny">Sunny</SelectItem>
                <SelectItem value="Cloudy">Cloudy</SelectItem>
                <SelectItem value="Rainy">Rainy</SelectItem>
                <SelectItem value="Snowy">Snowy</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Traffic</Label>
            <Select value={state.traffic} onValueChange={(val) => setState({ ...state, traffic: val })}>
              <SelectTrigger>
                <div className="flex items-center">
                  <CarFront className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Traffic" />
                </div>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Light">Light Traffic</SelectItem>
                <SelectItem value="Moderate">Moderate Traffic</SelectItem>
                <SelectItem value="Heavy">Heavy Traffic</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="pt-6">
          <Button
            className="w-full rounded-full h-14 text-lg font-medium transition-all hover:scale-[1.02] active:scale-[0.98]"
            onClick={nextStep}
            disabled={!isFormValid}
          >
            Begin Analysis
          </Button>
        </div>
      </div>

      {showDriverModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card p-6 rounded-xl w-full max-w-md border border-border shadow-lg">
            <h2 className="text-xl font-bold mb-4">Add New Driver Profile</h2>
            <div className="space-y-4 [&>div:nth-child(2)]:hidden [&>div:nth-child(3)]:hidden">
              <div className="space-y-2">
                <Label>Full Name</Label>
                <Input value={newDriver.isim} onChange={e => setNewDriver({...newDriver, isim: e.target.value})} placeholder="e.g. John Smith" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Age</Label>
                  <Input type="number" value={newDriver.yas} onChange={e => setNewDriver({...newDriver, yas: parseInt(e.target.value) || 30})} />
                </div>
                <div className="space-y-2">
                  <Label>Stress Tendency (0.0 - 1.0)</Label>
                  <Input type="number" step="0.1" value={newDriver.stres_egilimi} onChange={e => setNewDriver({...newDriver, stres_egilimi: parseFloat(e.target.value) || 0.5})} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Fatigue Threshold (0 - 100)</Label>
                <Input type="number" value={newDriver.yorgunluk_esigi} onChange={e => setNewDriver({...newDriver, yorgunluk_esigi: parseInt(e.target.value) || 60})} />
                <p className="text-xs text-muted-foreground">Higher threshold means more fatigue-resistant.</p>
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <Button variant="ghost" onClick={() => setShowDriverModal(false)}>Cancel</Button>
                <Button onClick={handleAddDriver} disabled={!newDriver.isim}>Save to System</Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
