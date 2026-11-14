# CompressOS — Business Model & Market Launch Roadmap

**Branch:** `exp/business-model-launch`  
**Start date:** 2026-11-14  
**Target public pilot readiness:** 2026-12-20  
**Target commercial launch:** 2027-01-15

## 1. Commercial thesis

CompressOS is not sold as "a local model" or "a Linux customization".

The commercial product is a **managed local-AI enablement service for Windows and Linux PCs**:

- assess existing hardware;
- install and configure local AI;
- optimize the operating system and memory/runtime layer;
- install a workload profile;
- provide a local technical agent for health monitoring and self-repair;
- provide 24/7 AI support;
- schedule preventive and condition-based maintenance;
- escalate only unresolved cases to a human technician;
- retain a client/device history sufficient to reproduce, maintain, and upgrade the installation.

The client keeps ownership and control of the computer. CompressOS records what was installed and how it behaves; it does not require permanent unrestricted remote control.

## 2. Initial products

### 2.1 Creator Profile

Target:
- social-media creators;
- freelancers;
- agencies;
- small content teams.

Capabilities:
- local chat/prompt assistant;
- image generation;
- image upscaling;
- transcription;
- speech/audio tools where supported;
- workflow automation;
- optional cloud overflow for workloads that exceed local hardware;
- future video-generation integration when hardware or remote providers permit it.

### 2.2 Business Profile

Target:
- small businesses;
- professional offices;
- consultants;
- teams with private documents and internal knowledge.

Capabilities:
- local assistant;
- private document/RAG workflows;
- database and internal-tool integrations;
- n8n workflows;
- MCP integrations;
- optional cloud routing;
- backup and maintenance policy.

### 2.3 Personal AI Profile

Target:
- individuals wanting private/local AI.

Capabilities:
- local chat;
- optional speech;
- basic document support;
- simple maintenance;
- optional cloud fallback.

## 3. Supported operating systems

The product must be designed as **Windows + Linux from the beginning**.

### Linux
Initial supported family:
- Ubuntu / Linux Mint / Lubuntu-derived environments.

Bootstrap:
- `install-linux.sh`

### Windows
Initial supported family:
- Windows 10/11 x64.

Bootstrap:
- `install-windows.ps1`

The bootstrap must detect platform differences instead of assuming paths, privilege model, package manager, shell, GPU stack, or service manager.

## 4. Reproducible installation architecture

The installation must become reproducible before commercial launch.

Target structure:

```text
provisioning/
├── linux/
│   ├── install-linux.sh
│   ├── detect-hardware.sh
│   └── service-setup/
├── windows/
│   ├── install-windows.ps1
│   ├── detect-hardware.ps1
│   └── service-setup/
├── profiles/
│   ├── creator/
│   ├── business/
│   └── personal/
├── manifests/
└── rollback/
```

Every installation must produce an **installation manifest** containing:

- client/device identifier;
- operating system;
- CPU;
- RAM;
- GPU;
- VRAM when available;
- disk capacity/free space;
- AI runtimes installed;
- Lemonade version;
- installed backends;
- installed models;
- selected profile;
- configuration changes;
- services enabled;
- validation results;
- installation date;
- installer version;
- rollback information.

## 5. Local Node Agent

Each managed computer receives a lightweight local agent.

The Node Agent is not a general surveillance agent.

### It monitors by default

- Lemonade server health;
- loaded-model status;
- AI backend health;
- MCP servers;
- n8n instance/workflows where installed;
- configured harness/services;
- CPU load;
- RAM;
- swap/ZRAM/Zswap state where supported;
- GPU/VRAM telemetry where supported;
- free disk;
- model caches;
- application logs;
- service restarts;
- failed updates;
- dependency availability;
- network reachability required by configured services.

### It must NOT monitor by default

- browser page content;
- passwords;
- cookies;
- personal documents;
- private prompts;
- unrelated application activity;
- clipboard contents.

Any deeper diagnostic collection must be opt-in and auditable.

## 6. Self-healing policy

The local Node Agent may automatically execute only allow-listed low-risk repairs.

Examples:

- restart a failed non-critical AI service;
- retry a model load;
- verify backend executables;
- clear explicitly safe temporary caches;
- rotate logs;
- re-run a health probe;
- restore known-good service configuration;
- detect a missing dependency and recommend installation.

Actions requiring explicit approval:

- package removal;
- major upgrades;
- driver replacement;
- privileged registry/system configuration changes;
- deleting model data;
- changing firewall rules;
- remote-control session;
- destructive cleanup.

Each automatic action must create a log entry:

```text
timestamp
device_id
detected_problem
action_attempted
result
before_state
after_state
agent_version
```

## 7. Support model

### Tier 0 — Local self-heal

The local Node Agent detects and resolves safe, known failures.

### Tier 1 — 24/7 Support AI

A central support bot has access to:

- product documentation;
- installation procedures;
- known issues;
- troubleshooting trees;
- model/backend compatibility matrix;
- anonymized device health information authorized by the client;
- the client's own installation manifest.

It answers common questions and guides recovery.

### Tier 2 — Human technician

Escalation occurs when:

- local repair failed;
- support bot confidence is insufficient;
- privileged changes are required;
- hardware failure is suspected;
- client requests human support.

Remote access is initiated only after client authorization and should expire after the support session.

## 8. Client and device database

Minimum entities:

### Client
- client_id
- name/company
- contact channels
- purchased plan
- support level
- billing status

### Device
- device_id
- client_id
- OS
- hardware summary
- installed profile
- installation date
- last_seen
- health status

### Installation
- installer version
- manifest
- models
- backends
- configuration
- validation outcome

### Health event
- timestamp
- severity
- component
- event
- automatic resolution
- unresolved status

### Maintenance
- due date
- trigger
- maintenance type
- completed date
- result

### Support ticket
- source: local agent / support bot / client / technician
- severity
- diagnostic summary
- actions
- outcome

### Remote session
- authorization
- start
- end
- operator
- actions performed

## 9. Maintenance model

Maintenance is both **scheduled** and **condition-based**.

### Scheduled maintenance

Creator:
- automatic weekly health summary;
- monthly preventive maintenance;
- quarterly full configuration review.

Business:
- automatic weekly health summary;
- monthly preventive maintenance;
- quarterly security/configuration review.

Personal:
- monthly health summary;
- quarterly preventive maintenance.

### Condition-based triggers

Create a maintenance event when:

- free disk falls below threshold;
- cache growth exceeds expected range;
- repeated backend crashes occur;
- model load repeatedly fails;
- AI runtime update is available and approved;
- GPU driver/backend incompatibility appears;
- service health degrades;
- repeated OOM or memory pressure is observed;
- n8n/MCP dependency becomes unavailable;
- configuration drift is detected.

## 10. Maintenance automation

Automation should resolve routine work without a technician.

Pipeline:

```text
Node Agent
   ↓
Health Event
   ↓
Rule Engine
   ↓
Safe auto-fix?
 ├─ yes → repair → verify → close
 └─ no
      ↓
Support AI analysis
      ↓
Can guide client?
 ├─ yes → guided recovery → verify
 └─ no
      ↓
Ticket + technician
```

n8n may orchestrate:
- reminders;
- health reports;
- ticket creation;
- maintenance scheduling;
- client notifications;
- support escalation;
- follow-up surveys;
- billing events.

## 11. Observability and failure prediction

The objective is to identify degradation before the client reports a failure.

Collect only technical telemetry necessary for support:

- service uptime;
- restart counts;
- error counts;
- disk pressure;
- memory pressure;
- swap pressure;
- backend health;
- model-load failures;
- response latency;
- GPU availability;
- update failures.

Do not collect client content unless explicitly required and authorized.

Initial prediction model can be rule-based. Machine-learning prediction is a later phase.

## 12. Commercial plans

### Install
One-time:
- hardware assessment;
- profile installation;
- validation;
- basic documentation.

### Care
Recurring:
- 24/7 AI support;
- health monitoring;
- scheduled maintenance;
- update management;
- incident history.

### Business
Recurring:
- Care;
- business integrations;
- RAG/database workflows;
- n8n/MCP automation;
- priority escalation;
- custom workflows.

Prices are intentionally not fixed in this document until installation time and support cost are measured during the pilot.

## 13. Human scaling model

Do not hire based solely on client count. Hire when support workload becomes a development bottleneck.

### Founder
- product;
- architecture;
- difficult incidents;
- commercial strategy.

### First technical operator
Hire when either condition is sustained for 3 weeks:
- >10 human support interventions/week; or
- >8 hours/week of founder time consumed by routine support/maintenance.

Responsibilities:
- scheduled maintenance;
- ticket triage;
- approved remote sessions;
- installation supervision;
- documentation of recurring incidents.

### Second operator
Consider when:
- first operator remains >70% utilized for 4 weeks; or
- >50 active Care/Business devices with increasing human escalation rate.

## 14. Documentation required before launch

The Support AI must have:

- installation guide;
- Windows troubleshooting guide;
- Linux troubleshooting guide;
- Lemonade guide;
- GPU/backend compatibility guide;
- model-loading guide;
- n8n guide;
- MCP guide;
- Node Agent recovery guide;
- update/rollback guide;
- remote-support policy;
- privacy policy;
- maintenance policy;
- escalation tree;
- known-issues database.

## 15. Launch gates

No commercial advertisement should claim the service is ready until all mandatory gates are met.

### Gate A — Reproducible installation
- [ ] Linux bootstrap works on a clean supported system.
- [ ] Windows bootstrap works on a clean supported system.
- [ ] Installation manifest is generated.
- [ ] rollback path is documented.

### Gate B — AI runtime
- [ ] local chat profile works;
- [ ] image-generation profile works on supported hardware;
- [ ] transcription path works;
- [ ] cloud fallback can be configured optionally.

### Gate C — Monitoring
- [ ] Node Agent reports health;
- [ ] service failures are detected;
- [ ] safe self-heal is tested;
- [ ] telemetry is privacy-bounded.

### Gate D — Support
- [ ] Support AI is deployed;
- [ ] documentation is indexed;
- [ ] contact channel exists;
- [ ] escalation to human works;
- [ ] ticket is recorded.

### Gate E — Maintenance
- [ ] scheduled maintenance creation works;
- [ ] condition-based trigger works;
- [ ] maintenance completion is logged;
- [ ] client notification works.

### Gate F — Pilot
- [ ] at least three clean installations tested;
- [ ] at least one Windows installation;
- [ ] at least one Linux installation;
- [ ] 7-day unattended health run completed;
- [ ] recovery from at least three simulated failures documented.

Only after Gates A–F pass should the project generate public sales copy claiming production readiness.

## 16. Objectives and dates

### 2026-11-14 → 2026-11-16 — Freeze MVP scope
Deliverables:
- [ ] Creator MVP definition;
- [ ] Business MVP definition;
- [ ] Personal MVP definition;
- [ ] supported OS matrix;
- [ ] minimum hardware matrix;
- [ ] privacy/remote-access boundaries.

### 2026-11-17 → 2026-11-23 — Reproducible installers
Deliverables:
- [ ] `install-linux.sh`;
- [ ] `install-windows.ps1`;
- [ ] hardware detection;
- [ ] installation manifest;
- [ ] dry-run/check mode;
- [ ] rollback plan.

### 2026-11-24 → 2026-12-01 — Node Agent v0.1
Deliverables:
- [ ] service health checks;
- [ ] Lemonade checks;
- [ ] n8n/MCP checks;
- [ ] disk/memory/GPU probes;
- [ ] local event log;
- [ ] first safe self-heal rules.

### 2026-12-02 → 2026-12-08 — Client database + maintenance automation
Deliverables:
- [ ] database schema;
- [ ] device registration;
- [ ] health events;
- [ ] maintenance scheduler;
- [ ] ticket creation;
- [ ] n8n automation for reminders/escalations.

### 2026-12-09 → 2026-12-15 — 24/7 Support AI
Deliverables:
- [ ] support knowledge base;
- [ ] support bot deployment;
- [ ] client/device context lookup;
- [ ] escalation flow;
- [ ] human contact channel.

### 2026-12-16 → 2026-12-20 — Pilot readiness
Deliverables:
- [ ] Creator profile validated;
- [ ] Linux clean-install validation;
- [ ] Windows clean-install validation;
- [ ] unattended health run;
- [ ] simulated failure recovery.

### 2026-12-21 → 2027-01-05 — Pilot
Objectives:
- [ ] three pilot installations;
- [ ] measure installation time;
- [ ] measure support workload;
- [ ] record recurring failure classes;
- [ ] validate maintenance cadence;
- [ ] revise pricing assumptions.

### 2027-01-06 → 2027-01-12 — Commercial packaging
Deliverables:
- [ ] final product names;
- [ ] plan matrix;
- [ ] pricing;
- [ ] onboarding flow;
- [ ] terms/privacy/support boundaries;
- [ ] landing-page copy.

### 2027-01-15 — Commercial launch target
Launch only if mandatory gates are green.

## 17. Immediate next actions

1. Create the repository structure for provisioning and support.
2. Convert the current working Lemonade Linux setup into a machine-readable installation manifest.
3. Implement Linux hardware detection first because a validated Linux machine already exists.
4. Implement the equivalent Windows detector and bootstrap.
5. Define Creator Profile v0.1 using currently validated local capabilities.
6. Start Node Agent with read-only health checks before any auto-repair behavior.
7. Implement the client/device database before the first external pilot.

## 18. Definition of success

The business is ready to scale when a new supported computer can go from a clean OS to a validated AI profile with:

- one bootstrap action;
- deterministic installation;
- automatic hardware/profile selection;
- recorded manifest;
- automatic health reporting;
- documented support path;
- scheduled maintenance;
- minimal founder intervention.

The target is not "zero failures". The target is **failures that are detected, classified, logged, and resolved through a repeatable process**.
