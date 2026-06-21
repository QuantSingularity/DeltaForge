# DeltaForge - Infrastructure

MetaTrader platform integrations for Forex trading.

## MetaTrader 5 (MQL5)

```
mql5/
├── DeltaForge_EA.mq5          # Main Expert Advisor
└── Include/
    ├── Strategies.mqh         # 26 strategy implementations
    ├── RiskManager.mqh        # Position sizing, SL/TP, trail stops
    ├── MLFilter.mqh           # ML signal scoring
    └── DisplayPanel.mqh       # On-chart display panel
```

**Setup:**

1. Copy `mql5/DeltaForge_EA.mq5` → `<MT5 Data>/MQL5/Experts/`
2. Copy `mql5/Include/*.mqh` → `<MT5 Data>/MQL5/Include/`
3. Compile in MetaEditor (F7)
4. Attach to chart and configure inputs

## MetaTrader 4 (MQL4)

```
mql4/
└── DeltaForge_EA.mq4          # Single-file EA with all 26 strategies inline
```

**Setup:**

1. Copy `mql4/DeltaForge_EA.mq4` → `<MT4 Data>/MQL4/Experts/`
2. Compile in MetaEditor (F7)
3. Attach to chart and the panel appears automatically

## Supported Timeframes

`M15` · `H1` · `H4` · `D1`

## Trail Stop Types (all 5 implemented in both EAs)

| Type            | MT5/MQL5           | MT4/MQL4         |
| --------------- | ------------------ | ---------------- |
| ATR             | `TRAIL_ATR`        | `InpTrailType=0` |
| Percentage      | `TRAIL_PERCENT`    | `InpTrailType=1` |
| Dollar          | `TRAIL_DOLLAR`     | `InpTrailType=2` |
| Time-tightening | `TRAIL_TIME`       | `InpTrailType=3` |
| Volatility      | `TRAIL_VOLATILITY` | `InpTrailType=4` |

## Containers & Orchestration

```
docker/
├── Dockerfile.backend        # Trading engine + FastAPI API (python:3.12-slim)
├── Dockerfile.frontend       # Vite build served by nginx
├── nginx.conf                # SPA + /api + /ws reverse proxy
├── requirements-api.txt      # FastAPI / uvicorn / pydantic
└── docker-compose.yml        # Full local stack

k8s/
└── deltaforge.yaml           # Namespace, ConfigMap, Deployments, Services,
                              # Ingress, HorizontalPodAutoscaler

terraform/
├── main.tf                   # ECR repos + VPC + EKS cluster + Secrets Manager
├── variables.tf
├── outputs.tf
└── terraform.tfvars.example
```

### Local (Docker Compose)

```bash
docker compose -f infrastructure/docker/docker-compose.yml up --build
# Dashboard: http://localhost:8080
# API docs:  http://localhost:8000/docs
```

### Kubernetes

```bash
# Provide exchange credentials (never committed)
kubectl create secret generic deltaforge-secrets -n deltaforge \
  --from-literal=EXCHANGE_API_KEY=... --from-literal=EXCHANGE_API_SECRET=...

kubectl apply -f infrastructure/k8s/deltaforge.yaml
```

### Provisioning (Terraform)

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars   # edit for your account
terraform init
terraform plan
terraform apply
```
