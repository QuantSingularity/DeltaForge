# DeltaForge — infrastructure as code.
#
# Provisions container registries for the backend and frontend images and an
# EKS cluster to run them, wired to the Kubernetes manifests in ../k8s.
#
# This is a reference module: review variables in variables.tf and run
#   terraform init && terraform plan
# against your own AWS account before applying.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project     = "DeltaForge"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ── Container registries ──────────────────────────────────────────────
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project}-backend"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project}-frontend"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

# ── Networking ────────────────────────────────────────────────────────
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project}-${var.environment}"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway = true
  single_nat_gateway = var.environment != "prod"
}

# ── Kubernetes cluster ────────────────────────────────────────────────
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "${var.project}-${var.environment}"
  cluster_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = true

  eks_managed_node_groups = {
    workers = {
      min_size       = var.node_min
      max_size       = var.node_max
      desired_size   = var.node_desired
      instance_types = [var.node_instance_type]
    }
  }
}

# ── Secrets store for exchange credentials ────────────────────────────
resource "aws_secretsmanager_secret" "exchange" {
  name        = "${var.project}/${var.environment}/exchange-credentials"
  description = "DeltaForge exchange API key + secret (internal use only)"
}
