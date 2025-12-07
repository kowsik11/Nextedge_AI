const API_BASE = "http://localhost:8000"; // Or use environment variable

export interface GoogleSheetsConnection {
    status: 'active' | 'expired' | 'error' | 'disconnected';
    spreadsheet_name?: string;
    last_sync_at?: string;
}

export interface Spreadsheet {
    id: string;
    name: string;
}

export async function getGoogleSheetsStatus(userId: string, accessToken?: string): Promise<GoogleSheetsConnection> {
    const res = await fetch(`${API_BASE}/google-sheets/status?user_id=${userId}`, {
        headers: {
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
    });
    if (!res.ok) {
        throw new Error("Failed to get Google Sheets status");
    }
    return res.json();
}

export async function connectGoogleSheets(userId: string, accessToken?: string): Promise<void> {
    const res = await fetch(`${API_BASE}/google-sheets/auth?user_id=${userId}`, {
        headers: {
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
    });
    if (!res.ok) {
        throw new Error("Failed to initiate Google Sheets connection");
    }
    const data = await res.json();
    window.location.href = data.auth_url;
}

export async function disconnectGoogleSheets(userId: string, accessToken?: string): Promise<void> {
    const res = await fetch(`${API_BASE}/google-sheets/disconnect?user_id=${userId}`, {
        method: "POST",
        headers: {
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
    });
    if (!res.ok) {
        throw new Error("Failed to disconnect Google Sheets");
    }
}

export async function listSpreadsheets(userId: string, accessToken?: string): Promise<Spreadsheet[]> {
    const res = await fetch(`${API_BASE}/google-sheets/spreadsheets?user_id=${userId}`, {
        headers: {
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
    });
    if (!res.ok) {
        throw new Error("Failed to list spreadsheets");
    }
    return res.json();
}

export async function selectSpreadsheet(userId: string, spreadsheetId: string, accessToken?: string): Promise<void> {
    const res = await fetch(`${API_BASE}/google-sheets/select-spreadsheet`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({ user_id: userId, spreadsheet_id: spreadsheetId }),
    });
    if (!res.ok) {
        throw new Error("Failed to select spreadsheet");
    }
}

export async function syncEmailToSheets(
    userId: string,
    emailId: string,
    accessToken?: string,
    overrides?: { reasoning?: string; classification?: string }
): Promise<{ success: boolean; row_number: number; spreadsheet_url: string }> {
    const res = await fetch(`${API_BASE}/google-sheets/sync-email`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({
            user_id: userId,
            email_id: emailId,
            ...overrides
        }),
    });

    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to sync email to sheets");
    }

    return res.json();
}
