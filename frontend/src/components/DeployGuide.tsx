import React from 'react';

const CodeBlock: React.FC<{ children: string }> = ({ children }) => (
    <pre className="bg-slate-900 dark:bg-slate-950 text-slate-100 rounded-lg p-4 overflow-x-auto text-sm font-mono my-3" tabIndex={0}>
        <code>{children.trim()}</code>
    </pre>
);

const Code: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <code className="text-[0.85em] bg-muted px-1 py-0.5 rounded font-mono">{children}</code>
);

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
    <section className="space-y-3">
        <h2 className="text-lg font-bold border-b pb-2">{title}</h2>
        {children}
    </section>
);

type EnvVar = { name: string; required?: boolean; description: React.ReactNode };

const ENV_GROUPS: { title: string; vars: EnvVar[] }[] = [
    {
        title: 'Inti',
        vars: [
            { name: 'ADMIN_PASSWORD', required: true, description: 'Kata sandi admin. Setelah diganti dari nilai bawaan, setiap perubahan pengaturan memerlukannya. Selama masih bawaan, siapa pun yang bisa membuka instance ini bisa mengubah pengaturan.' },
            { name: 'BMKG_API_URL', description: <>Alamat API sumber data BMKG. Bawaan: <Code>https://bmkg-api.dhanypedia.com</Code></> },
            { name: 'DEMO_MODE', description: <><Code>true</Code> menjadikan instance demo publik yang hanya bisa dibaca dan mengaktifkan trial 24 jam.</> },
            { name: 'TZ', description: <>Zona waktu, dipakai untuk jam tenang. Bawaan: <Code>Asia/Jakarta</Code></> },
            { name: 'CLIENT_IP_HEADER', description: <>Header berisi alamat pengunjung dari reverse proxy Anda, untuk pembatasan laju. Cloudflare: <Code>CF-Connecting-IP</Code>, nginx: <Code>X-Real-IP</Code>.</> },
        ],
    },
    {
        title: 'Telegram',
        vars: [
            { name: 'TELEGRAM_BOT_TOKEN', description: 'Token bot dari @BotFather.' },
            { name: 'TELEGRAM_CHAT_ID', description: 'Chat ID pribadi atau grup yang menerima notifikasi.' },
        ],
    },
    {
        title: 'Channel lain',
        vars: [
            { name: 'DISCORD_WEBHOOK_URL', description: 'URL incoming webhook Discord.' },
            { name: 'SLACK_WEBHOOK_URL', description: 'URL incoming webhook Slack.' },
            { name: 'SMTP_HOST / SMTP_USER / SMTP_PASSWORD', description: 'Pengiriman email lewat SMTP.' },
            { name: 'GENERIC_WEBHOOK_URL', description: 'Endpoint webhook JSON milik Anda.' },
        ],
    },
];

export const DeployGuide: React.FC = () => {
    return (
        <div className="w-full max-w-3xl mx-auto space-y-10 pb-10">
            <div>
                <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Pasang sendiri</h1>
                <p className="text-muted-foreground">
                    Jalankan BMKG Alert di server Anda sendiri. Yang dibutuhkan hanya Docker.
                </p>
            </div>

            <Section title="Yang perlu disiapkan">
                <ul className="list-disc pl-5 space-y-1 text-sm">
                    <li>Docker dan Docker Compose (v2).</li>
                    <li>Host Linux atau macOS, atau Windows dengan WSL2.</li>
                    <li>Token bot Telegram untuk notifikasi. Opsional, tetapi disarankan.</li>
                </ul>
            </Section>

            <Section title="Langkah pemasangan">
                <ol className="space-y-6 text-sm list-decimal pl-5 marker:font-semibold">
                    <li>
                        <p className="font-semibold">Salin repositori</p>
                        <CodeBlock>{`git clone https://github.com/dhanyyudi/bmkg-alert.git
cd bmkg-alert`}</CodeBlock>
                    </li>
                    <li>
                        <p className="font-semibold">Buat berkas .env</p>
                        <CodeBlock>{`cp .env.example .env`}</CodeBlock>
                        <p>Isi minimal kata sandi admin dan kredensial Telegram:</p>
                        <CodeBlock>{`ADMIN_PASSWORD=kata-sandi-yang-kuat
TELEGRAM_BOT_TOKEN=token-dari-BotFather
TELEGRAM_CHAT_ID=123456789`}</CodeBlock>
                    </li>
                    <li>
                        <p className="font-semibold">Jalankan container</p>
                        <CodeBlock>{`docker compose up -d`}</CodeBlock>
                        <p>
                            Buka <Code>http://localhost:3000</Code>. Halaman penyiapan akan memandu langkah berikutnya.
                        </p>
                    </li>
                </ol>
            </Section>

            <Section title="Variabel lingkungan">
                <p className="text-sm">Semua pengaturan server ada di berkas <Code>.env</Code>.</p>
                <div className="overflow-x-auto rounded-lg border">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-muted">
                            <tr>
                                <th scope="col" className="py-2 px-3 font-semibold">Variabel</th>
                                <th scope="col" className="py-2 px-3 font-semibold">Wajib?</th>
                                <th scope="col" className="py-2 px-3 font-semibold">Keterangan</th>
                            </tr>
                        </thead>
                        {ENV_GROUPS.map(group => (
                            <tbody key={group.title}>
                                <tr className="border-t bg-muted/50">
                                    <th scope="colgroup" colSpan={3} className="py-1.5 px-3 text-xs font-semibold text-left">{group.title}</th>
                                </tr>
                                {group.vars.map(v => (
                                    <tr key={v.name} className="border-t align-top">
                                        <td className="py-2 px-3 font-mono text-xs whitespace-nowrap">{v.name}</td>
                                        <td className="py-2 px-3 whitespace-nowrap">{v.required ? 'Wajib' : 'Opsional'}</td>
                                        <td className="py-2 px-3 min-w-[14rem]">{v.description}</td>
                                    </tr>
                                ))}
                            </tbody>
                        ))}
                    </table>
                </div>
            </Section>

            <Section title="Menyiapkan bot Telegram">
                <ol className="list-decimal pl-5 space-y-1 text-sm">
                    <li>Buka Telegram dan cari <Code>@BotFather</Code>.</li>
                    <li>Kirim <Code>/newbot</Code>, lalu ikuti petunjuknya sampai bot dibuat.</li>
                    <li>Salin Bot Token ke <Code>TELEGRAM_BOT_TOKEN</Code> di <Code>.env</Code>.</li>
                    <li>Kirim <Code>/start</Code> ke <Code>@userinfobot</Code> dan salin angka Chat ID yang dibalasnya.</li>
                    <li>Isi angka itu ke <Code>TELEGRAM_CHAT_ID</Code> di <Code>.env</Code>.</li>
                </ol>
            </Section>

            <Section title="Reverse proxy (opsional)">
                <p className="text-sm">
                    Secara bawaan port <Code>3000</Code> dibuka langsung. Untuk memakai domain dengan HTTPS, taruh reverse proxy di depannya.
                    Container frontend sudah meneruskan semua permintaan <Code>/api</Code> ke backend, jadi cukup satu layanan yang dibuka.
                </p>
                <h3 className="text-sm font-semibold">Caddy</h3>
                <CodeBlock>{`bmkg-alert.example.com {
    reverse_proxy localhost:3000
}`}</CodeBlock>
                <h3 className="text-sm font-semibold">Nginx</h3>
                <CodeBlock>{`server {
    server_name bmkg-alert.example.com;
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}`}</CodeBlock>
            </Section>

            <Section title="Pembaruan dan pemeliharaan">
                <p className="text-sm">Tarik image terbaru lalu jalankan ulang:</p>
                <CodeBlock>{`docker compose pull
docker compose up -d`}</CodeBlock>
                <p className="text-sm">Melihat log:</p>
                <CodeBlock>{`docker compose logs -f`}</CodeBlock>
                <p className="text-sm">Menghentikan layanan:</p>
                <CodeBlock>{`docker compose down`}</CodeBlock>
            </Section>

            <Section title="Penyimpanan data">
                <p className="text-sm">
                    Basis data dan konfigurasi disimpan di <Code>./data/backend/</Code> pada host. Cadangkan direktori ini untuk menjaga pengaturan dan riwayat peringatan.
                </p>
                <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 rounded-lg p-3 text-sm text-amber-900 dark:text-amber-100">
                    <p>
                        <strong>Izin direktori.</strong> Jika backend gagal menyala karena galat izin, pastikan direktori data dimiliki UID 1000:
                    </p>
                    <CodeBlock>{`sudo chown -R 1000:1000 ./data/`}</CodeBlock>
                </div>
            </Section>
        </div>
    );
};
