import React from 'react';
import { Terminal, Server, Key, Bell, RefreshCw, HardDrive, Globe, ChevronRight } from 'lucide-react';

const CodeBlock: React.FC<{ children: string; language?: string }> = ({ children, language = 'bash' }) => (
    <pre className="bg-slate-900 dark:bg-slate-950 text-slate-100 rounded-lg p-4 overflow-x-auto text-sm font-mono my-3">
        <code>{children.trim()}</code>
    </pre>
);

const Step: React.FC<{ number: number; title: string; children: React.ReactNode }> = ({ number, title, children }) => (
    <div className="flex gap-4 mb-8">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold mt-0.5">
            {number}
        </div>
        <div className="flex-1">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-2">{title}</h3>
            <div className="text-sm text-slate-600 dark:text-slate-400 space-y-2">
                {children}
            </div>
        </div>
    </div>
);

const Section: React.FC<{ icon: React.ReactNode; title: string; children: React.ReactNode }> = ({ icon, title, children }) => (
    <section className="mb-10">
        <div className="flex items-center gap-2 mb-4">
            <span className="text-blue-600 dark:text-blue-400">{icon}</span>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">{title}</h2>
        </div>
        {children}
    </section>
);

const EnvRow: React.FC<{ name: string; required?: boolean; description: string; example?: string }> = ({ name, required, description, example }) => (
    <tr className="border-t border-slate-200 dark:border-slate-700">
        <td className="py-2 pr-4 font-mono text-xs text-blue-700 dark:text-blue-300 whitespace-nowrap">{name}</td>
        <td className="py-2 pr-4">
            {required ? (
                <span className="text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-1.5 py-0.5 rounded">required</span>
            ) : (
                <span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded">optional</span>
            )}
        </td>
        <td className="py-2 text-sm text-slate-600 dark:text-slate-400">
            {description}
            {example && <span className="block font-mono text-xs text-slate-400 dark:text-slate-500 mt-0.5">e.g. {example}</span>}
        </td>
    </tr>
);

export const DeployGuide: React.FC = () => {
    return (
        <div className="max-w-3xl mx-auto py-8 px-4">
            {/* Hero */}
            <div className="mb-10">
                <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Self-Hosting Guide</h1>
                <p className="text-slate-500 dark:text-slate-400">
                    Run BMKG Alert on your own server in minutes. All you need is Docker.
                </p>
            </div>

            {/* Requirements */}
            <Section icon={<Server className="h-5 w-5" />} title="Requirements">
                <ul className="list-none space-y-1.5 text-sm text-slate-600 dark:text-slate-400">
                    <li className="flex items-center gap-2"><ChevronRight className="h-3 w-3 text-blue-500" /> Docker and Docker Compose (v2)</li>
                    <li className="flex items-center gap-2"><ChevronRight className="h-3 w-3 text-blue-500" /> Any Linux / macOS host (or Windows with WSL2)</li>
                    <li className="flex items-center gap-2"><ChevronRight className="h-3 w-3 text-blue-500" /> A Telegram bot token (for notifications) — optional but recommended</li>
                </ul>
            </Section>

            {/* Quick Start */}
            <Section icon={<Terminal className="h-5 w-5" />} title="Quick Start">
                <Step number={1} title="Clone the repository">
                    <CodeBlock>{`git clone https://github.com/dhanyyudi/bmkg-alert.git
cd bmkg-alert`}</CodeBlock>
                </Step>

                <Step number={2} title="Create your .env file">
                    <p>Copy the example file and edit it:</p>
                    <CodeBlock>{`cp .env.example .env`}</CodeBlock>
                    <p>At minimum, set your admin password and Telegram credentials:</p>
                    <CodeBlock language="env">{`ADMIN_PASSWORD=your-strong-password
TELEGRAM_BOT_TOKEN=1234567890:AAxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789`}</CodeBlock>
                </Step>

                <Step number={3} title="Start the containers">
                    <CodeBlock>{`docker compose up -d`}</CodeBlock>
                    <p>Open <strong className="text-slate-800 dark:text-slate-200">http://localhost:3000</strong> — the Setup Wizard will guide you through the rest.</p>
                </Step>
            </Section>

            {/* Environment Variables */}
            <Section icon={<Key className="h-5 w-5" />} title="Environment Variables">
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">All settings live in your <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">.env</code> file.</p>
                <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-800">
                                <th className="py-2 px-3 text-xs font-semibold text-slate-600 dark:text-slate-300">Variable</th>
                                <th className="py-2 px-3 text-xs font-semibold text-slate-600 dark:text-slate-300"></th>
                                <th className="py-2 px-3 text-xs font-semibold text-slate-600 dark:text-slate-300">Description</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800 px-3">
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td colSpan={3} className="py-1.5 px-3 text-xs font-semibold text-slate-400 uppercase tracking-wide bg-slate-50/50 dark:bg-slate-800/50">Core</td>
                            </tr>
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td className="py-2 px-3 font-mono text-xs text-blue-700 dark:text-blue-300 whitespace-nowrap">ADMIN_PASSWORD</td>
                                <td className="py-2 px-3"><span className="text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-1.5 py-0.5 rounded">required</span></td>
                                <td className="py-2 px-3 text-sm text-slate-600 dark:text-slate-400">Admin login password — change from default!</td>
                            </tr>
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td className="py-2 px-3 font-mono text-xs text-blue-700 dark:text-blue-300 whitespace-nowrap">DEMO_MODE</td>
                                <td className="py-2 px-3"><span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded">optional</span></td>
                                <td className="py-2 px-3 text-sm text-slate-600 dark:text-slate-400"><code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">true</code> = read-only public demo, enables 24h trial</td>
                            </tr>
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td className="py-2 px-3 font-mono text-xs text-blue-700 dark:text-blue-300 whitespace-nowrap">TZ</td>
                                <td className="py-2 px-3"><span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded">optional</span></td>
                                <td className="py-2 px-3 text-sm text-slate-600 dark:text-slate-400">Timezone, default: <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">Asia/Jakarta</code></td>
                            </tr>
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td colSpan={3} className="py-1.5 px-3 text-xs font-semibold text-slate-400 uppercase tracking-wide bg-slate-50/50 dark:bg-slate-800/50">Telegram</td>
                            </tr>
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td className="py-2 px-3 font-mono text-xs text-blue-700 dark:text-blue-300 whitespace-nowrap">TELEGRAM_BOT_TOKEN</td>
                                <td className="py-2 px-3"><span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded">optional</span></td>
                                <td className="py-2 px-3 text-sm text-slate-600 dark:text-slate-400">Bot token from @BotFather</td>
                            </tr>
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td className="py-2 px-3 font-mono text-xs text-blue-700 dark:text-blue-300 whitespace-nowrap">TELEGRAM_CHAT_ID</td>
                                <td className="py-2 px-3"><span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded">optional</span></td>
                                <td className="py-2 px-3 text-sm text-slate-600 dark:text-slate-400">Your personal or group chat ID (for admin alerts)</td>
                            </tr>
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td colSpan={3} className="py-1.5 px-3 text-xs font-semibold text-slate-400 uppercase tracking-wide bg-slate-50/50 dark:bg-slate-800/50">Other Channels</td>
                            </tr>
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td className="py-2 px-3 font-mono text-xs text-blue-700 dark:text-blue-300 whitespace-nowrap">DISCORD_WEBHOOK_URL</td>
                                <td className="py-2 px-3"><span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded">optional</span></td>
                                <td className="py-2 px-3 text-sm text-slate-600 dark:text-slate-400">Discord incoming webhook URL</td>
                            </tr>
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td className="py-2 px-3 font-mono text-xs text-blue-700 dark:text-blue-300 whitespace-nowrap">SLACK_WEBHOOK_URL</td>
                                <td className="py-2 px-3"><span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded">optional</span></td>
                                <td className="py-2 px-3 text-sm text-slate-600 dark:text-slate-400">Slack incoming webhook URL</td>
                            </tr>
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td className="py-2 px-3 font-mono text-xs text-blue-700 dark:text-blue-300 whitespace-nowrap">SMTP_HOST / SMTP_USER / SMTP_PASSWORD</td>
                                <td className="py-2 px-3"><span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded">optional</span></td>
                                <td className="py-2 px-3 text-sm text-slate-600 dark:text-slate-400">Email via SMTP</td>
                            </tr>
                            <tr className="border-t border-slate-200 dark:border-slate-700">
                                <td className="py-2 px-3 font-mono text-xs text-blue-700 dark:text-blue-300 whitespace-nowrap">GENERIC_WEBHOOK_URL</td>
                                <td className="py-2 px-3"><span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded">optional</span></td>
                                <td className="py-2 px-3 text-sm text-slate-600 dark:text-slate-400">Custom JSON webhook endpoint</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </Section>

            {/* Notifications */}
            <Section icon={<Bell className="h-5 w-5" />} title="Setting Up Telegram">
                <ol className="list-none space-y-2 text-sm text-slate-600 dark:text-slate-400">
                    {[
                        'Open Telegram and search for @BotFather',
                        'Send /newbot and follow the prompts to create your bot',
                        'Copy the Bot Token → set as TELEGRAM_BOT_TOKEN in .env',
                        'Get your Chat ID: send /start to @userinfobot and copy the number',
                        'Set it as TELEGRAM_CHAT_ID in .env',
                    ].map((step, i) => (
                        <li key={i} className="flex items-start gap-3">
                            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 flex items-center justify-center text-xs font-semibold mt-0.5">{i + 1}</span>
                            <span dangerouslySetInnerHTML={{ __html: step.replace(/@(\w+)/g, '<code class="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">@$1</code>').replace(/\/(\w+)/g, '<code class="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">/$1</code>').replace(/([A-Z_]{5,})/g, '<code class="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">$1</code>') }} />
                        </li>
                    ))}
                </ol>
            </Section>

            {/* Reverse Proxy */}
            <Section icon={<Globe className="h-5 w-5" />} title="Reverse Proxy (Optional)">
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
                    By default port <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">3000</code> is exposed directly. To serve from a domain with HTTPS, put a reverse proxy in front.
                </p>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Caddy</p>
                <CodeBlock language="caddy">{`bmkg-alert.example.com {
    reverse_proxy localhost:3000
}`}</CodeBlock>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-1 mt-4">Nginx</p>
                <CodeBlock language="nginx">{`server {
    server_name bmkg-alert.example.com;
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}`}</CodeBlock>
                <p className="text-sm text-slate-500 dark:text-slate-500 mt-2">
                    The frontend container handles all <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">/api</code> proxying to the backend — you only need to expose one service.
                </p>
            </Section>

            {/* Maintenance */}
            <Section icon={<RefreshCw className="h-5 w-5" />} title="Updates & Maintenance">
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">Pull the latest images and restart:</p>
                <CodeBlock>{`docker compose pull
docker compose up -d`}</CodeBlock>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-4 mb-2">To view logs:</p>
                <CodeBlock>{`docker compose logs -f`}</CodeBlock>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-4 mb-2">To stop:</p>
                <CodeBlock>{`docker compose down`}</CodeBlock>
            </Section>

            {/* Data Persistence */}
            <Section icon={<HardDrive className="h-5 w-5" />} title="Data Persistence">
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
                    All data (database, configuration) is stored in <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">./data/backend/</code> on the host. Back up this directory to preserve your setup.
                </p>
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 text-sm text-amber-800 dark:text-amber-200">
                    <strong>Volume Permissions</strong> — If the backend fails to start with a permission error, ensure the data directory is owned by UID 1000:
                    <CodeBlock>{`sudo chown -R 1000:1000 ./data/`}</CodeBlock>
                </div>
            </Section>
        </div>
    );
};
