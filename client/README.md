# ProtoBox Admin UI

A modern Next.js admin interface for managing your ProtoBox MCP server.

## 🚀 Features

- **Action Management**: Create, edit, and delete MCP actions
- **Execution Monitoring**: Real-time execution tracking and logs
- **Secret Management**: Secure storage for API keys and tokens
- **Analytics Dashboard**: Usage metrics and performance insights
- **Workspace Management**: Multi-tenant workspace support
- **Authentication**: Integrated with Clerk for secure access

## 📋 Prerequisites

- Node.js 18+ 
- npm or yarn
- ProtoBox MCP Server running (see ../server)

## 🛠️ Setup

1. **Install dependencies**:
```bash
npm install
```

2. **Environment Configuration**:
Create a `.env.local` file:
```env
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_key
CLERK_SECRET_KEY=your_clerk_secret

# ProtoBox API
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_MCP_URL=http://localhost:8080/mcp

# App Configuration
NEXT_PUBLIC_APP_NAME=ProtoBox
```

3. **Run development server**:
```bash
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to see the admin UI.

## 🏗️ Project Structure

```
client/
├── app/                    # Next.js app directory
│   ├── dashboard/         # Dashboard pages
│   │   ├── actions/      # Action management
│   │   ├── executions/   # Execution monitoring
│   │   ├── secrets/      # Secret management
│   │   └── analytics/    # Analytics dashboard
│   └── (auth)/           # Authentication pages
├── components/            # Reusable components
│   ├── ui/               # Base UI components
│   └── ...               # Feature components
├── lib/                   # Utilities and helpers
└── public/               # Static assets
```

## 🔧 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## 🎨 UI Components

Built with:
- [Radix UI](https://www.radix-ui.com/) - Unstyled, accessible components
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
- [Recharts](https://recharts.org/) - Charting library
- [Lucide Icons](https://lucide.dev/) - Icon set

## 📚 Key Features

### Action Management
- Create REST, CODE_RUN, O3, and DATABASE actions
- Visual configuration builder
- Schema validation
- Test execution interface

### Execution Monitoring
- Real-time execution logs
- Success/failure metrics
- Performance tracking
- Retry capabilities

### Secret Management
- Encrypted storage
- API key generation
- Environment variable management
- Access control

### Analytics Dashboard
- Usage statistics
- Performance metrics
- Cost tracking
- User activity

## 🔒 Authentication

The admin UI uses [Clerk](https://clerk.com) for authentication:
- Email/password authentication
- OAuth providers (Google, GitHub)
- Multi-factor authentication
- Role-based access control

## 🚀 Deployment

### Vercel (Recommended)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-repo/protobox-admin)

### Docker
```bash
docker build -t protobox-admin .
docker run -p 3000:3000 protobox-admin
```

## 🤝 Contributing

See the main [CONTRIBUTING.md](../server/CONTRIBUTING.md) for guidelines.

## 📄 License

Same license as the ProtoBox MCP Server project.