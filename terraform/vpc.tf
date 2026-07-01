module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.1.0"

  name = "payflow-production-vpc"
  cidr = "10.0.0.0/16"

  # 2 Public Subnets (for potential load balancers), 2 Private Subnets (for apps/DB)
  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true # Keeps costs low for testing profiles

  tags = {
    Environment = "production"
    Project     = "payflow"
  }
}
