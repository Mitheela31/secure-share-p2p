# SecureShare - P2P File Sharing Application Documentation

## Project Overview

**SecureShare** is an academic project simulating a **Secure Peer-to-Peer File Sharing Application with End-to-End Encryption**. This is a **frontend-only implementation** that demonstrates P2P networking and encryption concepts through UI states, animations, and visual simulations—without requiring any backend infrastructure.

### Technology Stack

| Technology | Purpose |
|------------|---------|
| **React 18** | Component-based UI framework |
| **TypeScript** | Type-safe JavaScript |
| **Tailwind CSS** | Utility-first CSS framework |
| **Vite** | Fast build tool and dev server |
| **Lucide React** | Icon library |
| **React Router** | Client-side routing |
| **TanStack Query** | Data fetching and caching |

---

## Project Structure

```
src/
├── components/
│   ├── AuthPage.tsx          # Authentication (Login/Register)
│   ├── RoleSelection.tsx     # Sender/Receiver role picker
│   ├── SenderDashboard.tsx   # Sender's main interface
│   ├── ReceiverDashboard.tsx # Receiver's main interface
│   ├── FileTransfer.tsx      # File upload and send simulation
│   ├── FileReceive.tsx       # File receive and decrypt simulation
│   ├── TransferHistory.tsx   # Transfer history display
│   └── ui/                   # Reusable UI components (shadcn/ui)
├── pages/
│   ├── Index.tsx             # Main application entry point
│   └── NotFound.tsx          # 404 page
├── hooks/                    # Custom React hooks
├── lib/                      # Utility functions
├── index.css                 # Global styles and design system
└── main.tsx                  # Application bootstrap
```

---

## Application Flow

### State Machine

The application follows a linear state machine flow:

```
┌──────────┐     ┌─────────────┐     ┌──────────┐
│   Auth   │ ──► │ Role Select │ ──► │  Sender  │
└──────────┘     └─────────────┘     └──────────┘
                        │                  
                        │            ┌──────────┐
                        └──────────► │ Receiver │
                                     └──────────┘
```

### Application States

| State | Description |
|-------|-------------|
| `auth` | User authentication (login/register) |
| `role-select` | User chooses Sender or Receiver role |
| `sender` | Sender dashboard with file transfer capabilities |
| `receiver` | Receiver dashboard waiting for incoming files |

---

## Component Documentation

### 1. AuthPage (`src/components/AuthPage.tsx`)

**Purpose:** Handles user authentication with login and registration forms.

#### Features
- Toggle between **Sign In** and **Register** modes
- Form fields:
  - Username (min 3 characters)
  - Email (register only, validated)
  - Password (min 6 characters)
  - Confirm Password (register only)
- Password visibility toggle
- Real-time input validation with error messages
- Loading state with spinner during authentication
- Security badges (256-bit Encryption, Zero-Knowledge)

#### State Management
```typescript
interface FormData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}
```

#### Key Functions
| Function | Description |
|----------|-------------|
| `validateForm()` | Validates all form fields and returns boolean |
| `handleSubmit()` | Simulates authentication with 1.5s delay |
| `handleInputChange()` | Updates form state and clears field errors |

#### Props
```typescript
interface AuthPageProps {
  onLogin: (username: string) => void;
}
```

---

### 2. RoleSelection (`src/components/RoleSelection.tsx`)

**Purpose:** Allows authenticated users to choose their role (Sender or Receiver).

#### Features
- Two interactive role cards with hover effects
- Visual distinction between Sender and Receiver roles
- Role capabilities displayed as badges
- Security status indicator
- Logout option

#### Props
```typescript
interface RoleSelectionProps {
  username: string;
  onSelectRole: (role: 'sender' | 'receiver') => void;
  onLogout: () => void;
}
```

---

### 3. SenderDashboard (`src/components/SenderDashboard.tsx`)

**Purpose:** Main interface for users sending files.

#### Features
- Display of available receivers (mock data)
- Online/Offline status indicators
- Connection request workflow
- File transfer integration
- Transfer history toggle

#### Mock Receivers
```typescript
const MOCK_RECEIVERS = [
  { id: '1', name: 'Alice_Secure', online: true },
  { id: '2', name: 'Bob_Crypto', online: true },
  { id: '3', name: 'Charlie_Dev', online: false },
  { id: '4', name: 'Diana_Net', online: true },
  { id: '5', name: 'Eve_Shield', online: false },
];
```

#### Connection States
| State | Description |
|-------|-------------|
| `idle` | No connection, awaiting receiver selection |
| `requesting` | Connection request sent, awaiting acceptance |
| `connected` | Secure connection established, ready for transfer |
| `transferring` | File transfer in progress |
| `complete` | Transfer completed successfully |

#### Props
```typescript
interface SenderDashboardProps {
  username: string;
  onBack: () => void;
  onLogout: () => void;
  transfers: TransferRecord[];
  onNewTransfer: (transfer: TransferRecord) => void;
}
```

---

### 4. ReceiverDashboard (`src/components/ReceiverDashboard.tsx`)

**Purpose:** Main interface for users receiving files.

#### Features
- Real-time connection status panel
- Incoming connection request notifications
- Accept/Reject connection buttons
- File receive workflow
- Transfer history

#### Simulated Behavior
- Automatically receives connection request after 3 seconds
- Displays encryption status (AES-256 Active)
- Shows P2P listening status

#### Connection States
| State | Description |
|-------|-------------|
| `waiting` | Listening for incoming connections |
| `request` | Connection request received |
| `connected` | Connection accepted |
| `receiving` | File transfer in progress |
| `complete` | File received and decrypted |

#### Incoming Request Structure
```typescript
interface IncomingRequest {
  id: string;
  sender: string;
  fileName: string;
  fileSize: string;
}
```

---

### 5. FileTransfer (`src/components/FileTransfer.tsx`)

**Purpose:** Handles file selection and simulates encrypted file transfer.

#### Features
- Drag-and-drop file upload
- Click-to-browse file selection
- File preview with name and size
- Multi-stage transfer simulation
- Visual progress indicator
- Step-by-step status updates

#### Transfer Stages
```
1. Encrypting ────► (0-33%)
2. Establishing ──► (34-50%)
3. Sending ───────► (51-100%)
4. Complete ──────► Done
```

#### Status Messages
| Status | Message | Icon |
|--------|---------|------|
| `encrypting` | "Encrypting file with AES-256..." | Lock |
| `establishing` | "Establishing secure channel..." | Shield |
| `sending` | "Sending encrypted file..." | Send |
| `complete` | "Transfer complete!" | CheckCircle2 |

#### Props
```typescript
interface FileTransferProps {
  receiverName: string;
  onTransferComplete: (fileName: string, fileSize: string) => void;
  onCancel: () => void;
}
```

---

### 6. FileReceive (`src/components/FileReceive.tsx`)

**Purpose:** Simulates receiving and decrypting incoming files.

#### Features
- Incoming file notification with encryption badges
- Receive & Decrypt action button
- Multi-stage receive simulation
- Progress indicator
- Success confirmation

#### Receive Stages
```
1. Receiving ─────► (0-60%)
2. Decrypting ────► (61-100%)
3. Complete ──────► Done
```

#### Status Messages
| Status | Message | Icon |
|--------|---------|------|
| `receiving` | "Receiving encrypted file..." | Download |
| `decrypting` | "Decrypting with private key..." | Lock |
| `complete` | "File received successfully!" | CheckCircle2 |

#### Props
```typescript
interface FileReceiveProps {
  senderName: string;
  fileName: string;
  fileSize: string;
  onReceiveComplete: () => void;
}
```

---

### 7. TransferHistory (`src/components/TransferHistory.tsx`)

**Purpose:** Displays a chronological list of completed file transfers.

#### Features
- Sent/Received type indicators
- File details (name, size, timestamp)
- Sender/Receiver information
- Encryption status badges
- Empty state handling

#### Transfer Record Structure
```typescript
interface TransferRecord {
  id: string;
  fileName: string;
  fileSize: string;
  sender: string;
  receiver: string;
  timestamp: Date;
  type: 'sent' | 'received';
}
```

---

### 8. Index Page (`src/pages/Index.tsx`)

**Purpose:** Root component managing global application state and routing.

#### State Management
```typescript
type AppState = 'auth' | 'role-select' | 'sender' | 'receiver';

const [appState, setAppState] = useState<AppState>('auth');
const [username, setUsername] = useState('');
const [transfers, setTransfers] = useState<TransferRecord[]>([]);
```

#### Handler Functions
| Function | Description |
|----------|-------------|
| `handleLogin(user)` | Sets username and transitions to role selection |
| `handleSelectRole(role)` | Transitions to sender or receiver dashboard |
| `handleLogout()` | Clears state and returns to auth |
| `handleBackToRoleSelect()` | Returns to role selection |
| `handleNewTransfer(transfer)` | Adds new transfer to history |

---

## Design System

### Color Palette

| Token | HSL Value | Usage |
|-------|-----------|-------|
| `--background` | 240 15% 5% | Main background |
| `--foreground` | 210 40% 98% | Primary text |
| `--primary` | 263 70% 58% | Electric Violet - CTAs, highlights |
| `--secondary` | 190 95% 45% | Cyan - Accents |
| `--success` | 160 84% 40% | Success states |
| `--warning` | 38 92% 50% | Warning states |
| `--destructive` | 0 84% 60% | Error states |
| `--muted` | 240 15% 15% | Subdued elements |

### Typography

| Font Family | Usage |
|-------------|-------|
| **Inter** | Primary sans-serif for UI text |
| **JetBrains Mono** | Monospace for code/technical data |

### Custom Components

#### Glass Card
```css
.glass-card {
  background: linear-gradient(145deg, hsl(240 15% 10% / 0.8), hsl(240 15% 6% / 0.8));
  backdrop-blur: 24px;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.75rem;
}
```

#### Cyber Border
Animated gradient border effect using CSS masks:
```css
.cyber-border::before {
  background: linear-gradient(135deg, primary, secondary, primary);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: exclude;
}
```

#### Cyber Buttons
- `.cyber-btn` - Primary gradient button with glow on hover
- `.cyber-btn-secondary` - Secondary cyan gradient button

#### Cyber Input
```css
.cyber-input {
  background: hsl(var(--input));
  border: 1px solid hsl(var(--border) / 0.5);
  /* Focus: glow effect with ring */
}
```

### Animations

| Animation | Description |
|-----------|-------------|
| `animate-shield` | Pulsing scale and glow effect |
| `animate-encrypt` | Opacity and scale pulse |
| `animate-data-flow` | Horizontal movement |
| `animate-float` | Vertical floating motion |
| `animate-fade-in-up` | Entry animation from below |
| `pulse-dot` | Expanding ring effect |
| `scan-line` | Vertical scanning effect |

### Glow Effects
```css
--glow-primary: 0 0 20px hsl(263 70% 58% / 0.5);
--glow-secondary: 0 0 20px hsl(190 95% 45% / 0.5);
--glow-success: 0 0 20px hsl(160 84% 40% / 0.5);
```

---

## Workflow Diagrams

### Complete User Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER AUTHENTICATION                           │
├─────────────────────────────────────────────────────────────────────┤
│  [Login Form] ──► Validate ──► Simulate Auth ──► [Role Selection]  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│        SENDER WORKFLOW          │  │       RECEIVER WORKFLOW          │
├─────────────────────────────────┤  ├─────────────────────────────────┤
│ 1. View available receivers     │  │ 1. Wait for connection request  │
│ 2. Select online receiver       │  │ 2. Accept/Reject connection     │
│ 3. Connection request sent      │  │ 3. Secure channel established   │
│ 4. Connection established       │  │ 4. Receive encrypted file       │
│ 5. Upload file (drag/browse)    │  │ 5. Decrypt file                 │
│ 6. Encrypt file (AES-256)       │  │ 6. Store securely               │
│ 7. Establish secure channel     │  │ 7. Success confirmation         │
│ 8. Send encrypted file          │  │                                 │
│ 9. Transfer complete            │  │                                 │
└─────────────────────────────────┘  └─────────────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                    ┌─────────────────────────────────┐
                    │       TRANSFER HISTORY          │
                    ├─────────────────────────────────┤
                    │  • File name                    │
                    │  • File size                    │
                    │  • Sender/Receiver              │
                    │  • Timestamp                    │
                    │  • Status (Sent/Received)       │
                    │  • Encryption indicator         │
                    └─────────────────────────────────┘
```

### File Transfer Process (Sender)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  File Drop   │ ──► │  Encrypting  │ ──► │ Establishing │ ──► │   Sending    │
│  or Browse   │     │   AES-256    │     │   Channel    │     │    Data      │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                          0-33%               34-50%              51-100%
                              │                   │                   │
                              └───────────────────┴───────────────────┘
                                                  │
                                                  ▼
                                         ┌──────────────┐
                                         │   Complete   │
                                         │    ✓ 100%    │
                                         └──────────────┘
```

### File Receive Process (Receiver)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Pending    │ ──► │  Receiving   │ ──► │  Decrypting  │
│   (Click)    │     │    Data      │     │ Private Key  │
└──────────────┘     └──────────────┘     └──────────────┘
                          0-60%               61-100%
                              │                   │
                              └───────────────────┘
                                        │
                                        ▼
                               ┌──────────────┐
                               │   Complete   │
                               │ File Stored  │
                               └──────────────┘
```

---

## Security Concepts (Simulated)

This application simulates the following security concepts:

| Concept | Implementation |
|---------|----------------|
| **End-to-End Encryption** | Visual simulation of AES-256 encryption |
| **Zero-Knowledge** | Displayed as security badge |
| **P2P Connection** | Simulated connection request/accept flow |
| **Secure Channel** | Visual status indicators |
| **Private Key Decryption** | Simulated decryption animation |

---

## Responsive Design

The application is fully responsive with breakpoints:

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Mobile | < 640px | Single column, stacked layouts |
| Tablet | 640px - 1024px | Two-column grids |
| Desktop | > 1024px | Full multi-column layouts |

---

## Dependencies

### Core Dependencies
- `react`, `react-dom` - UI framework
- `react-router-dom` - Client-side routing
- `@tanstack/react-query` - Data fetching

### UI Dependencies
- `lucide-react` - Icon library
- `tailwindcss`, `tailwindcss-animate` - Styling
- `class-variance-authority`, `clsx`, `tailwind-merge` - Class utilities

### Font Dependencies
- `@fontsource/inter` - Primary font
- `@fontsource/jetbrains-mono` - Monospace font

### Radix UI Components
- Various `@radix-ui/react-*` packages for accessible UI primitives

---

## File Utility Functions

### `formatFileSize(bytes: number): string`
Converts bytes to human-readable format:
```typescript
if (bytes < 1024) return bytes + ' B';
if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
```

---

## Future Enhancements (Potential)

1. **Real Backend Integration** - Connect to actual P2P network
2. **WebRTC Implementation** - True peer-to-peer connections
3. **Actual Encryption** - Implement Web Crypto API
4. **User Persistence** - Database-backed user accounts
5. **File Storage** - Cloud or local storage integration
6. **Push Notifications** - Real-time connection alerts
7. **Audio Feedback** - Sound effects for transfers

---

## License

Academic project - For educational purposes only.

---

*Documentation generated for SecureShare P2P File Sharing Application*
*Version: 1.0.0*
