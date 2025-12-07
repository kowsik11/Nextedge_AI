import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, AlertCircle, FileSpreadsheet } from "lucide-react";
import {
    getGoogleSheetsStatus,
    connectGoogleSheets,
    disconnectGoogleSheets,
    listSpreadsheets,
    selectSpreadsheet,
    GoogleSheetsConnection,
    Spreadsheet,
} from "@/lib/googleSheets";
import { useToast } from "@/components/ui/use-toast";

interface GoogleSheetsConnectorProps {
    userId: string;
    accessToken?: string;
}

export function GoogleSheetsConnector({ userId, accessToken }: GoogleSheetsConnectorProps) {
    const [status, setStatus] = useState<GoogleSheetsConnection | null>(null);
    const [loading, setLoading] = useState(false);
    const [spreadsheets, setSpreadsheets] = useState<Spreadsheet[]>([]);
    const [selectedSheetId, setSelectedSheetId] = useState<string>("");
    const { toast } = useToast();

    const fetchStatus = async () => {
        try {
            const data = await getGoogleSheetsStatus(userId, accessToken);
            setStatus(data);
        } catch (error) {
            console.error(error);
            // Set a default disconnected status on error to avoid infinite loading
            setStatus({ status: 'disconnected' });
        }
    };

    useEffect(() => {
        if (userId) {
            fetchStatus();
        }
    }, [userId, accessToken]);

    const handleConnect = async () => {
        setLoading(true);
        try {
            await connectGoogleSheets(userId, accessToken);
            // Redirect happens in the function
        } catch (error) {
            console.error(error);
            toast({
                title: "Connection Failed",
                description: "Could not initiate Google Sheets connection.",
                variant: "destructive",
            });
            setLoading(false);
        }
    };

    const handleDisconnect = async () => {
        setLoading(true);
        try {
            await disconnectGoogleSheets(userId, accessToken);
            await fetchStatus();
            toast({
                title: "Disconnected",
                description: "Google Sheets integration removed.",
            });
        } catch (error) {
            console.error(error);
            toast({
                title: "Error",
                description: "Failed to disconnect.",
                variant: "destructive",
            });
        } finally {
            setLoading(false);
        }
    };

    const loadSpreadsheets = async () => {
        try {
            const sheets = await listSpreadsheets(userId, accessToken);
            setSpreadsheets(sheets);
        } catch (error) {
            console.error(error);
            toast({
                title: "Error",
                description: "Failed to list spreadsheets.",
                variant: "destructive",
            });
        }
    };

    const handleSheetSelect = async (sheetId: string) => {
        setLoading(true);
        try {
            await selectSpreadsheet(userId, sheetId, accessToken);
            setSelectedSheetId(sheetId);
            await fetchStatus();
            toast({
                title: "Spreadsheet Selected",
                description: "Emails will now sync to this sheet.",
            });
        } catch (error) {
            console.error(error);
            toast({
                title: "Error",
                description: "Failed to select spreadsheet.",
                variant: "destructive",
            });
        } finally {
            setLoading(false);
        }
    };

    if (!status) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <FileSpreadsheet className="h-5 w-5" />
                        Connect Google Sheets
                    </CardTitle>
                    <CardDescription>Loading status...</CardDescription>
                </CardHeader>
                <CardContent>
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </CardContent>
            </Card>
        );
    }

    const isConnected = status.status === "active";

    return (
        <Card className={isConnected ? "border-green-200 bg-green-50/50 dark:bg-green-900/10" : ""}>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                        <FileSpreadsheet className="h-5 w-5" />
                        Connect Google Sheets
                    </CardTitle>
                    {isConnected && (
                        <Badge variant="secondary" className="bg-green-100 text-green-700 hover:bg-green-100 dark:bg-green-900 dark:text-green-300">
                            <CheckCircle2 className="mr-1 h-3 w-3" />
                            Connected
                        </Badge>
                    )}
                </div>
                <CardDescription>
                    Sync emails and AI analysis directly to a Google Sheet.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {isConnected ? (
                    <div className="space-y-4">
                        <div className="text-sm">
                            <p className="text-muted-foreground mb-1">Active Spreadsheet:</p>
                            {status.spreadsheet_name ? (
                                <div className="font-medium flex items-center gap-2">
                                    <FileSpreadsheet className="h-4 w-4 text-green-600" />
                                    {status.spreadsheet_name}
                                </div>
                            ) : (
                                <div className="text-amber-600 flex items-center gap-2">
                                    <AlertCircle className="h-4 w-4" />
                                    No sheet selected
                                </div>
                            )}
                        </div>

                        {!status.spreadsheet_name && (
                            <div className="space-y-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={loadSpreadsheets}
                                    className="w-full"
                                >
                                    Select Spreadsheet
                                </Button>

                                {spreadsheets.length > 0 && (
                                    <Select onValueChange={handleSheetSelect}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Choose a sheet..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {spreadsheets.map((sheet) => (
                                                <SelectItem key={sheet.id} value={sheet.id}>
                                                    {sheet.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                )}
                            </div>
                        )}

                        {status.last_sync_at && (
                            <p className="text-xs text-muted-foreground">
                                Last synced: {new Date(status.last_sync_at).toLocaleString()}
                            </p>
                        )}
                    </div>
                ) : (
                    <div className="text-sm text-muted-foreground">
                        Connect your Google account to enable spreadsheet syncing.
                    </div>
                )}
            </CardContent>
            <CardFooter>
                {isConnected ? (
                    <Button variant="outline" onClick={handleDisconnect} disabled={loading}>
                        {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                        Disconnect
                    </Button>
                ) : (
                    <Button onClick={handleConnect} disabled={loading} className="w-full">
                        {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                        Connect Google Sheets
                    </Button>
                )}
            </CardFooter>
        </Card>
    );
}
