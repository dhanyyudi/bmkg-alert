import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Trash2, Send, MessageCircle, Eye, EyeOff, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Channel {
    id: number;
    channel_type: string;
    enabled: boolean;
    config: {
        bot_token?: string;
        chat_id?: string;
        name?: string;
    };
    created_at: string | null;
}

// ─── Component ────────────────────────────────────────────────────────────────

export const ChannelStep: React.FC = () => {
    const [channels, setChannels] = useState<Channel[]>([]);

    // Form state
    const [name, setName] = useState('');
    const [botToken, setBotToken] = useState('');
    const [chatId, setChatId] = useState('');
    const [showToken, setShowToken] = useState(false);
    const [adding, setAdding] = useState(false);

    // Per-channel test state
    const [testing, setTesting] = useState<number | null>(null);
    const [testStatus, setTestStatus] = useState<Record<number, 'ok' | 'fail'>>({});

    const fetchChannels = async () => {
        try {
            const res = await api.get<{ data: Channel[] }>('/channels');
            setChannels(res.data ?? []);
        } catch {
            // leave the list empty; the add form below still works
        }
    };

    useEffect(() => { fetchChannels(); }, []);

    const addChannel = async () => {
        const trimmedToken = botToken.trim();
        const trimmedChatId = chatId.trim();
        const trimmedName = name.trim();

        if (!trimmedToken) { toast.error('Bot Token wajib diisi'); return; }
        if (!trimmedChatId) { toast.error('Chat ID wajib diisi'); return; }
        if (!trimmedName) { toast.error('Nama alias wajib diisi'); return; }

        setAdding(true);
        try {
            await api.post('/channels', {
                channel_type: 'telegram',
                enabled: true,
                config: {
                    bot_token: trimmedToken,
                    chat_id: trimmedChatId,
                    name: trimmedName,
                },
            });
            setBotToken('');
            setChatId('');
            setName('');
            fetchChannels();
            toast.success(`Channel "${trimmedName}" berhasil ditambahkan`);
        } catch (e: any) {
            toast.error('Gagal menambahkan channel', {
                description: e?.message ?? 'Terjadi kesalahan tidak diketahui.',
            });
        } finally {
            setAdding(false);
        }
    };

    const removeChannel = async (id: number, label: string) => {
        try {
            await api.delete(`/channels/${id}`);
            fetchChannels();
            toast.success(`Channel "${label}" dihapus`);
        } catch (e: any) {
            toast.error('Gagal menghapus channel', { description: e?.message });
        }
    };

    const testChannel = async (id: number) => {
        setTesting(id);
        setTestStatus(s => { const n = { ...s }; delete n[id]; return n; });
        try {
            await api.post(`/channels/${id}/test`, {});
            setTestStatus(s => ({ ...s, [id]: 'ok' }));
            toast.success('Pesan tes terkirim', { description: 'Cek Telegram Anda.' });
        } catch (e: any) {
            setTestStatus(s => ({ ...s, [id]: 'fail' }));
            toast.error('Pesan tes gagal terkirim', {
                description: e?.message ?? 'Pastikan Bot Token dan Chat ID sudah benar.',
            });
        } finally {
            setTesting(null);
        }
    };

    return (
        <div className="space-y-5">

            {/* ── Guide ─────────────────────────────────────────────────────── */}
            <div className="rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-950 dark:border-blue-800 p-4 text-sm space-y-3">

                <div>
                    <p className="font-semibold text-blue-800 dark:text-blue-200 mb-1">
                        1. Dapatkan Bot Token dari @BotFather
                    </p>
                    <ol className="list-decimal pl-4 space-y-0.5 text-blue-700 dark:text-blue-300">
                        <li>Buka Telegram, cari <strong>@BotFather</strong></li>
                        <li>Ketik <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">/newbot</code> dan ikuti instruksinya</li>
                        <li>BotFather akan memberikan token berformat:<br />
                            <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded text-xs">
                                123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                            </code>
                        </li>
                    </ol>
                </div>

                <div>
                    <p className="font-semibold text-blue-800 dark:text-blue-200 mb-1">
                        2. Dapatkan Chat ID (pilih salah satu cara)
                    </p>
                    <div className="space-y-2 text-blue-700 dark:text-blue-300">

                        <div className="rounded bg-blue-100 dark:bg-blue-900/50 px-3 py-2">
                            <p className="font-semibold text-xs mb-1">
                                Cara A: lewat @userinfobot (termudah, tanpa token)
                            </p>
                            <ol className="list-decimal pl-4 space-y-0.5 text-xs">
                                <li>Buka chat/grup target di Telegram</li>
                                <li>Forward satu pesan dari sana ke <strong>@userinfobot</strong></li>
                                <li>Bot akan membalas dengan <em>Forwarded from: Chat ID: ...</em></li>
                                <li>Salin angkanya (contoh: <code>-1001234567890</code> untuk grup)</li>
                            </ol>
                        </div>

                        <div className="rounded bg-blue-100 dark:bg-blue-900/50 px-3 py-2">
                            <p className="font-semibold text-xs mb-1">
                                Cara B: lewat Telegram API (jika sudah punya token)
                            </p>
                            <ol className="list-decimal pl-4 space-y-0.5 text-xs">
                                <li>Tambahkan bot ke grup/channel, lalu kirim pesan apapun</li>
                                <li>
                                    Buka URL berikut di browser, ganti <code>TOKEN</code> dengan token bot Anda:
                                    <br />
                                    <code className="bg-blue-200 dark:bg-blue-900 px-1 rounded break-all text-xs">
                                        https://api.telegram.org/bot<strong>TOKEN</strong>/getUpdates
                                    </code>
                                </li>
                                <li>
                                    Cari <code>{'"chat":{"id":'}</code>. Angka setelahnya adalah Chat ID Anda
                                </li>
                                <li>
                                    Jika hasilnya <code>{"result:[]"}</code> (kosong), kirim pesan ulang ke bot lalu
                                    refresh URL tersebut
                                </li>
                            </ol>
                        </div>

                    </div>
                </div>

                <p className="text-blue-700 dark:text-blue-300 text-xs border-t border-blue-200 dark:border-blue-800 pt-2">
                    <strong>Nama alias</strong> adalah label bebas untuk channel ini di BMKG Alert,{' '}
                    <em>bukan</em> username bot. Contoh: <em>"Grup RT 05"</em>, <em>"Channel Keluarga"</em>,{' '}
                    <em>"Notif Pribadi"</em>.
                </p>
            </div>

            {/* ── Add channel form ──────────────────────────────────────────── */}
            <div className="space-y-3 p-4 border rounded-lg bg-muted/50">
                <h3 className="text-sm font-semibold">Tambah channel Telegram</h3>

                <div className="grid gap-3">
                    <div>
                        <label htmlFor="setup-channel-name" className="text-sm font-medium mb-1 block">
                            Nama alias <span className="font-normal text-muted-foreground">(wajib)</span>
                        </label>
                        <Input
                            id="setup-channel-name"
                            placeholder="Misalnya Grup Keluarga"
                            value={name}
                            onChange={e => setName(e.target.value)}
                        />
                    </div>

                    <div>
                        <label htmlFor="setup-channel-token" className="text-sm font-medium mb-1 block">
                            Bot Token <span className="font-normal text-muted-foreground">(wajib, dari @BotFather)</span>
                        </label>
                        <div className="relative">
                            <Input
                                id="setup-channel-token"
                                type={showToken ? 'text' : 'password'}
                                autoComplete="off"
                                placeholder="123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                                value={botToken}
                                onChange={e => setBotToken(e.target.value)}
                                className="pr-12 font-mono"
                            />
                            <button
                                type="button"
                                aria-label={showToken ? 'Sembunyikan token' : 'Tampilkan token'}
                                aria-pressed={showToken}
                                className="absolute right-0 top-0 h-full w-11 flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                onClick={() => setShowToken(v => !v)}
                            >
                                {showToken ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
                            </button>
                        </div>
                    </div>

                    <div>
                        <label htmlFor="setup-channel-chat" className="text-sm font-medium mb-1 block">
                            Chat ID <span className="font-normal text-muted-foreground">(wajib)</span>
                            <span className="ml-1 font-normal text-muted-foreground">
                                (negatif untuk grup/channel, positif untuk chat pribadi)
                            </span>
                        </label>
                        <Input
                            id="setup-channel-chat"
                            inputMode="numeric"
                            placeholder="-1001234567890 atau 987654321"
                            value={chatId}
                            onChange={e => setChatId(e.target.value)}
                            className="font-mono"
                        />
                    </div>

                    <Button onClick={addChannel} disabled={adding} className="w-full gap-2">
                        {adding
                            ? <Loader2 className="h-4 w-4 animate-spin" />
                            : <MessageCircle className="h-4 w-4" />
                        }
                        Tambah channel
                    </Button>
                </div>
            </div>

            {/* ── Active channels list ──────────────────────────────────────── */}
            <div className="space-y-2">
                <h3 className="text-sm font-semibold">Channel yang sudah ditambahkan</h3>
                {channels.length === 0 ? (
                    <div className="text-center p-4 border border-dashed rounded text-sm text-muted-foreground">
                        Belum ada channel. Isi formulir di atas untuk menambahkan bot Telegram.
                    </div>
                ) : (
                    channels.map(ch => {
                        const label = ch.config?.name ?? `Channel #${ch.id}`;
                        // The API already masks credentials
                        const maskedToken = ch.config?.bot_token ?? '-';
                        return (
                            <div
                                key={ch.id}
                                className="flex items-center justify-between flex-wrap p-3 border rounded-md bg-card gap-3"
                            >
                                <div className="flex items-center gap-3 min-w-0">
                                    <div className="bg-blue-100 dark:bg-blue-900 p-2 rounded-full shrink-0">
                                        <Send className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                    </div>
                                    <div className="min-w-0">
                                        <div className="flex items-center gap-2">
                                            <p className="font-medium text-sm truncate">{label}</p>
                                            <Badge variant="outline" className="shrink-0">
                                                {ch.channel_type}
                                            </Badge>
                                        </div>
                                        <p className="text-xs text-muted-foreground font-mono">
                                            Chat ID: {ch.config?.chat_id ?? '-'}
                                        </p>
                                        <p className="text-xs text-muted-foreground font-mono">
                                            Token: {maskedToken}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2 shrink-0">
                                    {testStatus[ch.id] === 'ok' && (
                                        <span className="inline-flex items-center gap-1 text-xs text-green-700 dark:text-green-400">
                                            <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Terkirim
                                        </span>
                                    )}
                                    {testStatus[ch.id] === 'fail' && (
                                        <span className="inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
                                            <XCircle className="h-4 w-4" aria-hidden="true" /> Gagal
                                        </span>
                                    )}
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        disabled={testing === ch.id}
                                        onClick={() => testChannel(ch.id)}
                                        className="gap-1"
                                    >
                                        {testing === ch.id
                                            ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                                            : <Send className="h-4 w-4" aria-hidden="true" />
                                        }
                                        Kirim tes
                                    </Button>
                                    <Button
                                        size="icon"
                                        variant="ghost"
                                        className="text-red-600 dark:text-red-400"
                                        aria-label={`Hapus channel ${label}`}
                                        onClick={() => removeChannel(ch.id, label)}
                                    >
                                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                                    </Button>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
};
