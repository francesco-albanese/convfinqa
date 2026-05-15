provider "aws" {
  region = var.region

  # Auth handled externally:
  # - Local dev: AWS profiles with assume_role in ~/.aws/config
  # - GitHub OIDC: configure-aws-credentials sets env vars

  default_tags {
    tags = {
      "franco:terraform_stack" = "convfinqa"
      "franco:managed_by"      = "terraform"
      "franco:environment"     = var.account_name
    }
  }
}

# Cross-account provider for Route53 writes in the shared-services zone.
# Used by modules/edge for ACM DNS validation records and the subdomain NS entry.
provider "aws" {
  alias  = "shared_services"
  region = var.region

  assume_role {
    role_arn = "arn:aws:iam::${var.shared_services_account_id}:role/${var.shared_services_role_name}"
  }

  default_tags {
    tags = {
      "franco:terraform_stack" = "convfinqa"
      "franco:managed_by"      = "terraform"
      "franco:environment"     = var.account_name
    }
  }
}
